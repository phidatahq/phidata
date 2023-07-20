from typing import List, Any, Optional, Dict, Iterator

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from phi.document import Document
from phi.llm.base import LLM
from phi.llm.conversation.schemas import Message
from phi.llm.conversation.storage.base import ConversationStorage
from phi.llm.knowledge.base import KnowledgeBase
from phi.llm.openai import OpenAIChat
from phi.utils.log import logger, set_log_level_to_debug


class Conversation(BaseModel):
    # Set log level to debug
    debug_logs: bool = False

    # LLM settings
    llm: LLM = OpenAIChat()
    llm_name: Optional[str] = None
    llm_messages: List[Message] = []

    # User settings
    user_id: str = "anonymous"
    user_persona: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None
    user_messages: List[Message] = []

    # Prompt settings
    system_prompt: Optional[str] = None
    # Chat history settings
    max_chat_history_messages: int = 6
    max_chat_history_tokens: Optional[int] = None
    include_responses_in_chat_history: bool = True

    # Usage data
    usage_data: Dict[str, Any] = {}

    # Knowledge base for conversation
    knowledge_base: Optional[KnowledgeBase] = None

    # Storage for conversation
    storage: Optional[ConversationStorage] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_logs", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @model_validator(mode="after")  # type: ignore
    def initialize_storage(self):
        if self.storage is not None:
            logger.debug("Initializing storage")
            self.storage.create()
            self.read_from_storage()  # type: ignore
        return self

    @property
    def conversation_id(self) -> Optional[int]:
        if self.storage is None:
            return None
        conversation = self.storage.read(self.user_id)
        if conversation is None:
            return None
        return conversation.get("id", None)

    @property
    def user_chat_history(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self.user_messages]

    @property
    def llm_chat_history(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self.llm_messages]

    def is_knowledge_base_up_to_date(self) -> bool:
        if self.knowledge_base is None:
            return False
        return False
        # return self.knowledge_base.up_to_date

    def load_knowledge_base(self, recreate: bool = False) -> None:
        """Loads the knowledge base"""
        if self.knowledge_base is None:
            return
        self.knowledge_base.load_knowledge_base(recreate=recreate)

    def get_system_prompt(self) -> str:
        """Return the system prompt for the conversation"""

        if self.system_prompt:
            return "\n".join([line.strip() for line in self.system_prompt.split("\n")])

        _system_prompt = ""
        if self.llm_name:
            _system_prompt += f"You are a chatbot named '{self.llm_name}'"
        else:
            _system_prompt += "You are a chatbot "

        if self.user_persona:
            _system_prompt += f"that is designed to help a '{self.user_persona}' with their work.\n"
        else:
            _system_prompt += "that is designed to help a user with their work.\n"

        _system_prompt += "If you don't know the answer, say 'I don't know'. You can ask follow up questions if needed."
        return _system_prompt

    def get_chat_history(self) -> Optional[str]:
        """Return a formatted chat history for the prompt"""

        if len(self.user_messages) == 0:
            return None

        chat_history = ""
        chat_history_messages: List[Message] = []
        for message in self.user_messages[::-1]:
            if message.role == "user":
                chat_history_messages.insert(0, message)
            if message.role == "assistant" and self.include_responses_in_chat_history:
                chat_history_messages.insert(0, message)
            if len(chat_history_messages) >= self.max_chat_history_messages:
                break

        for message in chat_history_messages:
            if message.role == "user":
                chat_history += "\n---\n"
            chat_history += f"{message.role.upper()}: {message.content}\n"
        return chat_history

    def get_references(self, question: str) -> Optional[str]:
        """Return relevant information from the knowledge base"""

        if self.knowledge_base is None:
            return None

        relevant_docs: List[Document] = self.knowledge_base.search(query=question)
        relevant_info = ""
        for doc in relevant_docs:
            relevant_info += f"---\n{doc.content}\n"
            doc_name = doc.name
            doc_page = doc.meta_data.get("page")
            if doc_name:
                ref = f"Title: {doc_name}"
                if doc_page:
                    ref += f", Page: {doc_page}"
                relevant_info += f"Reference: {ref}\n"
            relevant_info += "---\n"
        return relevant_info

    def get_user_prompt(self, question: str, references: Optional[str], chat_history: Optional[str]) -> str:
        """Build the user prompt given a question, references and chat_history"""

        _user_prompt = "Your task is to answer the following question "
        if self.user_persona:
            _user_prompt += f"for a '{self.user_persona}' "
        _user_prompt += "using the following information:\n"
        # Add question to the prompt
        _user_prompt += f"\nQuestion: {question}\n"

        # Add relevant_information to prompt
        if references:
            _user_prompt += f"""
                You can use the following references if they help you answer the question.
                If you use the information from the references, please cite them as a bulleted list at the end.
                START OF REFERENCES
                ```
                {references}
                ```
                END OF REFERENCES
                """

        # Add chat history to prompt
        if chat_history:
            _user_prompt += f"""
                You can use the following chat history if it helps you answer the question.
                START OF CHAT HISTORY
                ```
                {chat_history}
                ```
                END OF CHAT HISTORY
                """

        _user_prompt += "\nRemember, your task is to answer the following question using the provided information:\n"
        _user_prompt += f"Question: {question}\n"

        # Return the user prompt after removing newlines and indenting
        return "\n".join([line.strip() for line in _user_prompt.split("\n")])

    def review(self, question: str) -> Iterator[str]:
        logger.debug(f"Reviewing: {question}")

        # Build the system prompt
        system_prompt = self.get_system_prompt()

        # Build the user prompt
        references = self.get_references(question=question)
        chat_history = self.get_chat_history()
        user_prompt = self.get_user_prompt(question=question, references=references, chat_history=chat_history)

        # Create messages for the LLM
        messages: List[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        # Update user_messages and llm_messages
        # Add the question to user_messages
        self.user_messages.append(Message(role="user", content=question))
        # Add the system prompt to llm_messages if needed
        if len(self.llm_messages) == 0:
            self.llm_messages.append(Message(role="system", content=system_prompt))
        # Add the user prompt to llm_messages
        self.llm_messages.append(Message(role="user", content=user_prompt))

        # Log messages
        for message in messages:
            logger.debug(f"{message.role}: {message.content}")

        # Generate response
        response = ""
        response_tokens = 0
        for delta in self.llm.streaming_response(messages=[m.model_dump(exclude_none=True) for m in messages]):
            response += delta
            response_tokens += 1
            yield response

        logger.debug(f"Response: {response}")

        # Add response to user_messages
        self.user_messages.append(Message(role="assistant", content=response))
        # Add response to llm_messages
        self.llm_messages.append(Message(role="assistant", content=response))

        # Add response tokens to usage data
        if "response_tokens" in self.usage_data:
            self.usage_data["response_tokens"] += response_tokens
        else:
            self.usage_data["response_tokens"] = response_tokens

        # Add question to usage data
        if "questions" in self.usage_data:
            self.usage_data["questions"] += 1
        else:
            self.usage_data["questions"] = 1

        # Save conversation to storage
        self.save_to_storage()

    def read_from_storage(self) -> None:
        """Read existing conversation from storage"""
        if self.storage is None:
            return

        existing_conversation = self.storage.read(user_id=self.user_id)
        if existing_conversation is None:
            logger.debug(f"No conversation found for user: {self.user_id}")
            return

        logger.debug(f"Found existing conversation for user: {self.user_id}")
        # Values that should not be overwritten if provided
        if self.user_persona is None and existing_conversation.get("user_persona") is not None:
            self.user_persona = existing_conversation["user_persona"]
        if self.user_data is None and existing_conversation.get("user_data") is not None:
            self.user_data = existing_conversation["user_data"]

        # Update conversation using existing conversation
        user_chat_history = existing_conversation.get("user_chat_history")
        if user_chat_history is not None and len(user_chat_history) > 0:
            self.user_messages = [Message(**message) for message in user_chat_history]
        llm_chat_history = existing_conversation.get("llm_chat_history")
        if llm_chat_history is not None and len(llm_chat_history) > 0:
            self.llm_messages = [Message(**message) for message in llm_chat_history]
        if existing_conversation.get("usage_data") is not None:
            self.usage_data = existing_conversation["usage_data"]

    def save_to_storage(self) -> None:
        """Save the conversation to the storage"""
        if self.storage is None:
            return
        self.storage.upsert(
            user_id=self.user_id,
            user_persona=self.user_persona,
            user_data=self.user_data,
            user_chat_history=self.user_chat_history,
            llm_chat_history=self.llm_chat_history,
            usage_data=self.usage_data,
        )

    def end(self) -> None:
        """End the conversation"""
        self.user_messages = []
        self.llm_messages = []
        if self.storage is not None:
            self.storage.end(user_id=self.user_id)
