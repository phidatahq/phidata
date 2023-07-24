from typing import List, Any, Optional, Dict, Iterator

from pydantic import BaseModel, ConfigDict, field_validator

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
    # The name of this conversation.
    name: Optional[str] = None
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
    add_history_to_prompt: bool = True
    add_history_to_messages: bool = False

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

    @property
    def conversation_row(self) -> ConversationRow:
        """Return the conversation row"""

        return ConversationRow(
            id=self.id,
            name=self.name,
            user_id=self.user_id,
            user_persona=self.user_persona,
            user_data=self.user_data,
            is_active=True,
            history=self.history,
            usage_data=self.usage_data,
            created_at=None,
            updated_at=None,
        )

    @conversation_row.setter
    def conversation_row(self, conversation_row: ConversationRow):
        """Set the conversation row"""

        # Values that should be overwritten only if they are None
        if self.id is None and conversation_row.id is not None:
            self.id = conversation_row.id
        if self.name is None and conversation_row.name is not None:
            self.name = conversation_row.name
        if self.user_persona is None and conversation_row.user_persona is not None:
            self.user_persona = conversation_row.user_persona
        if self.user_data is None and conversation_row.user_data is not None:
            self.user_data = conversation_row.user_data

        # Update current conversation using existing conversation
        if conversation_row.history is not None:
            self.history.chat_history = conversation_row.history.chat_history
            self.history.llm_history = conversation_row.history.llm_history
            self.history.references = conversation_row.history.references
        if conversation_row.usage_data is not None:
            self.usage_data = conversation_row.usage_data

    @property
    def conversation_id(self) -> Optional[int]:
        if self.id is not None:
            return self.id

        # The create function creates a new conversation row in the database
        # and returns the ID of the new conversation.
        return self.start()

    def start(self) -> Optional[int]:
        """Creates a new conversation and returns the conversation ID
        that can be used to retrieve this conversation later"""

        _conversation: Optional[ConversationRow] = None

        if self.storage is not None:
            logger.debug("Initializing storage")
            self.storage.create()

            if self.id is not None:
                logger.debug(f"Reading conversation: {self.id}")
                # If the conversation ID is already set, read the conversation from the database
                _conversation = self.storage.read_conversation(conversation_id=self.id, user_id=self.user_id)
                if _conversation is None:
                    raise Exception(f"Conversation not found: {self.id}")
                logger.debug(f"Conversation found: {self.id}")
            else:
                logger.debug("Creating new conversation")
                # If the conversation ID is not set, create a new conversation in the database
                _conversation = self.storage.upsert_conversation(conversation=self.conversation_row)
                if _conversation is None:
                    raise Exception("Failed to create conversation")
                logger.debug(f"Created conversation: {_conversation.id}")

        if _conversation is not None:
            self.conversation_row = _conversation

        return self.id

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

    def get_user_prompt(
        self, question: str, references: Optional[str] = None, chat_history: Optional[str] = None
    ) -> str:
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
        chat_history = self.history.get_formatted_history() if self.add_history_to_prompt else None
        user_prompt = self.get_user_prompt(question=question, references=references, chat_history=chat_history)

        # Create messages for the LLM
        system_message = Message(role="system", content=system_prompt)
        user_message = Message(role="user", content=user_prompt)
        messages: List[Message] = [system_message, user_message]

        # Add messages to the history
        # Add the system prompt to the history - only added if this is the first message to the LLM
        self.history.add_system_prompt(message=system_message)
        # Add user question to the history - this is added to the chat history
        self.history.add_user_question(message=Message(role="user", content=question))
        # Add user prompt to the history - this is added to the llm history
        self.history.add_user_prompt(message=user_message)
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

        # Add response to the history - this is added to the chat and llm history
        self.history.add_llm_response(message=Message(role="assistant", content=response))

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

    def save_to_storage(self) -> None:
        """Save the conversation to the storage"""
        if self.storage is None:
            return
        self.storage.upsert_conversation(conversation=self.conversation_row)

    def end(self) -> None:
        """End the conversation"""
        if self.storage is not None:
            if self.id is not None:
                self.storage.end_conversation(conversation_id=self.id, user_id=self.user_id)
