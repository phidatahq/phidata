from textwrap import dedent
from typing import List, Any, Optional, Dict, Iterator

from phi.document import Document
from phi.llm.base import LLM
from phi.llm.conversation.schemas import Message
from phi.llm.conversation.storage.base import ConversationStorage
from phi.llm.knowledge.base import KnowledgeBase
from phi.llm.openai import OpenAIChat
from phi.utils.log import logger, set_log_level_to_debug


class Conversation:
    def __init__(
        self,
        llm: Optional[LLM] = None,
        llm_name: Optional[str] = None,
        user_id: Optional[str] = None,
        user_persona: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        storage: Optional[ConversationStorage] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        debug_logs: bool = False,
    ):
        # LLM parameters
        self.llm: LLM = llm or OpenAIChat()
        self.llm_name: Optional[str] = llm_name
        self._llm_messages: List[Message] = []

        # User parameters
        self.user_id: str = user_id or "anonymous"
        self.user_persona: Optional[str] = user_persona
        self.meta_data: Optional[Dict[str, Any]] = meta_data
        self._user_messages: List[Message] = []

        # System parameters
        self.system_prompt: Optional[str] = system_prompt

        # Set log level to debug
        if debug_logs:
            set_log_level_to_debug()

        # Usage data
        self.usage_data: Dict[str, Any] = {}

        # Conversation storage
        self.storage: Optional[ConversationStorage] = storage
        self.initialize_storage()

        # Knowledge base
        self.knowledge_base: Optional[KnowledgeBase] = knowledge_base

    @property
    def user_messages(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self._user_messages]

    @user_messages.setter
    def user_messages(self, messages: List[Dict[str, Any]]) -> None:
        self._user_messages = [Message(**message) for message in messages]

    @property
    def llm_messages(self) -> List[Dict[str, Any]]:
        return [message.model_dump(exclude_none=True) for message in self._llm_messages]

    @llm_messages.setter
    def llm_messages(self, messages: List[Dict[str, Any]]) -> None:
        self._llm_messages = [Message(**message) for message in messages]

    def save_to_storage(self) -> None:
        """Save the conversation to the storage"""
        if self.storage is None:
            return
        self.storage.upsert(
            user_id=self.user_id,
            user_persona=self.user_persona,
            user_messages=self.user_messages,
            llm_messages=self.llm_messages,
            meta_data=self.meta_data,
            usage_data=self.usage_data,
        )

    def read_from_storage(self) -> None:
        """Read the conversation from the storage"""
        if self.storage is None:
            return
        conversation = self.storage.read(user_id=self.user_id)
        if conversation is None:
            return
        self.user_persona = conversation["user_persona"]
        self.user_messages = conversation["user_messages"]
        self.llm_messages = conversation["llm_messages"]
        self.meta_data = conversation["meta_data"]
        self.usage_data = conversation["usage_data"]

    def initialize_storage(self) -> None:
        """Initialize the storage"""
        if self.storage is None:
            return
        self.storage.create()
        self.read_from_storage()

    def load_knowledge_base(self, recreate: bool = False) -> None:
        """Loads the knowledge base"""
        if self.knowledge_base is None:
            return
        self.knowledge_base.load_knowledge_base(recreate=recreate)

    def build_system_prompt(self) -> str:
        """Build the system prompt for the conversation"""

        if self.system_prompt:
            return self.system_prompt

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

    def build_question_context(self, question: str) -> Optional[str]:
        """Build the context for a question"""
        if self.knowledge_base is None:
            return None

        relevant_docs: List[Document] = self.knowledge_base.search(query=question)
        context = ""
        for doc in relevant_docs:
            context += f"---\n{doc.content}\n"
            doc_name = doc.name
            doc_page = doc.meta_data.get("page")
            if doc_name:
                ref = doc_name
                if doc_page:
                    ref += f" (Page {doc_page})"
                context += f"Reference: {ref}\n"
            context += "---\n"
        return context

    def build_chat_history(self) -> Optional[str]:
        """Build the chat history for the conversation"""
        if len(self._user_messages) == 0:
            return None

        chat_history = ""
        for message in self._user_messages:
            chat_history += f"{message.role}: {message.content}\n"
        return chat_history

    def get_question_prompt(self, question: str) -> str:
        """Build the user prompt for the conversation"""

        _question_prompt = "Your task is to answer the following question in the best way possible.\n"
        # Add question to prompt
        _question_prompt += f"\nQuestion: {question}\n"

        # Add context to prompt
        context = self.build_question_context(question=question)
        if context:
            _question_prompt += dedent(
                f"""
            You have access to the following information which you can use to answer the question if it helps.
            START OF INFORMATION
            ---
            {context}
            ---
            END OF INFORMATION
            """
            )

        # Add chat history to prompt
        chat_history = self.build_chat_history()
        if chat_history:
            _question_prompt += dedent(
                f"""
            You have access to the following chat history which you can use to answer the question if it helps.
            START OF CHAT HISTORY
            ---
            {chat_history}
            ---
            END OF CHAT HISTORY
            """
            )

        return dedent(_question_prompt)

    def review(self, question: str) -> Iterator[str]:
        logger.debug(f"Reviewing: {question}")

        # Add the system prompt to llm_messages
        if len(self._llm_messages) == 0:
            self._llm_messages.append(Message(role="system", content=self.build_system_prompt()))

        # Add the question prompt to llm_messages
        self._llm_messages.append(Message(role="user", content=self.get_question_prompt(question=question)))
        for message in self._llm_messages:
            logger.debug(f"{message.role}: {message.content}")

        # Add the question to user_messages
        self._user_messages.append(Message(role="user", content=question))

        # Generate response
        response = ""
        response_tokens = 0
        for delta in self.llm.streaming_response(
            messages=[m.model_dump(exclude_none=True) for m in self._llm_messages]
        ):
            response += delta
            response_tokens += 1
            yield response

        logger.debug(f"Response: {response}")

        # Add response to user_messages
        self._user_messages.append(Message(role="assistant", content=response))
        # Add response to llm_messages
        self._llm_messages.append(Message(role="assistant", content=response))
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

    def end(self) -> None:
        """End the conversation"""
        self.user_messages = []
        self.llm_messages = []
        if self.storage is None:
            return
        self.storage.end(user_id=self.user_id)
