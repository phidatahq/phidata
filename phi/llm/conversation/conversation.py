from typing import List, Any, Optional, Dict, Iterator

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from phi.document import Document
from phi.llm.base import LLM
from phi.llm.schemas import Message, References
from phi.llm.conversation.schemas import ConversationRow
from phi.llm.storage.base import LLMStorage
from phi.llm.history.base import LLMHistory
from phi.llm.history.simple import SimpleConversationHistory
from phi.llm.knowledge.base import LLMKnowledgeBase
from phi.llm.openai import OpenAIChat
from phi.utils.log import logger, set_log_level_to_debug


class Conversation(BaseModel):
    # The ID of this conversation.
    id: Optional[int] = None
    # Set log level to debug
    debug_logs: bool = False
    # Send monitoring data to phidata.com
    monitoring: bool = False

    # LLM settings
    llm: LLM = OpenAIChat()
    llm_name: Optional[str] = None
    system_prompt: Optional[str] = None

    # User settings
    user_id: str = "anonymous"
    user_persona: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None

    # Usage data
    usage_data: Dict[str, Any] = {}

    # Conversation history
    history: LLMHistory = SimpleConversationHistory()

    # Knowledge base for the LLM
    knowledge_base: Optional[LLMKnowledgeBase] = None

    # Conversation storage
    storage: Optional[LLMStorage] = None

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

    def get_id(self) -> Optional[int]:
        if self.id is not None:
            return self.id

        if self.storage is not None:
            conversation: Optional[ConversationRow] = self.storage.read(self.user_id)
            if conversation is not None:
                return conversation.id
        return None

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

        return self.history.get_formatted_history()

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
        system_message = Message(role="system", content=system_prompt)
        user_message = Message(role="user", content=user_prompt)
        messages: List[Message] = [system_message, user_message]

        # Add messages to the history
        # Add user question to the chat history
        self.history.add_chat_history(message=Message(role="user", content=question))
        # Add the system message to the history
        self.history.add_system_message(message=system_message)
        # Add the user message to the llm history
        self.history.add_llm_history(message=user_message)

        # Add references to the history
        if references:
            self.history.add_references(references=References(question=question, references=references))

        # Log messages
        for message in self.history.chat_history:
            logger.debug(f"{message.role}: {message.content}")

        # Generate response
        response = ""
        response_tokens = 0
        for delta in self.llm.streaming_response(messages=[m.model_dump(exclude_none=True) for m in messages]):
            response += delta
            response_tokens += 1
            yield response

        logger.debug(f"Response: {response}")

        # Add response to chat history
        self.history.add_chat_history(message=Message(role="assistant", content=response))

        # Add response to llm history
        self.history.add_llm_history(message=Message(role="assistant", content=response))

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
