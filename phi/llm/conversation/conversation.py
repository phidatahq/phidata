from logging import Logger
from textwrap import dedent
from typing import List, Any, Optional, Dict, Iterator

from pydantic import BaseModel, ConfigDict

from phi.document import Document
from phi.llm.base import LLM
from phi.llm.conversation.schemas import Message
from phi.llm.conversation.storage.base import ConversationStorage
from phi.llm.knowledge.base import KnowledgeBase
from phi.llm.openai import OpenAIChat
from phi.utils.log import logger


class Conversation(BaseModel):
    """Model for managing a conversation"""

    # LLM parameters
    llm: LLM = OpenAIChat()
    llm_name: Optional[str] = None
    llm_tone: Optional[str] = None

    # User parameters
    user_id: Optional[str] = None
    user_persona: Optional[str] = None

    # Log messages
    log_messages: bool = False
    logger: Logger = logger

    _user_messages: List[Message] = []
    _llm_messages: List[Message] = []

    usage_data: Dict[str, Any] = {}

    storage: Optional[ConversationStorage] = None
    knowledge_base: Optional[KnowledgeBase] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def user_messages(self) -> List[Dict[str, Any]]:
        return [message.model_dump() for message in self._user_messages]

    @user_messages.setter
    def user_messages(self, messages: List[Dict[str, Any]]) -> None:
        self._user_messages = [Message(**message) for message in messages]

    @property
    def llm_messages(self) -> List[Dict[str, Any]]:
        return [message.model_dump() for message in self._llm_messages]

    @llm_messages.setter
    def llm_messages(self, messages: List[Dict[str, Any]]) -> None:
        self._llm_messages = [Message(**message) for message in messages]

    def load_knowledge_base(self, recreate: bool = False) -> None:
        """Loads the knowledge base"""
        if self.knowledge_base is None:
            return
        self.knowledge_base.load_knowledge_base(recreate=recreate)

    def build_system_prompt(self) -> str:
        """Build the system prompt for the conversation"""

        _system_prompt = ""
        if self.llm_name:
            _system_prompt += f"You are a chatbot named '{self.llm_name}' "
        else:
            _system_prompt += "You are a chatbot "

        if self.user_persona:
            _system_prompt += f"designed to answer questions from a '{self.user_persona}'.\n"
        else:
            _system_prompt += "designed to answer questions from a user.\n"

        if self.llm_tone:
            _system_prompt += f"Speak to them in a '{self.llm_tone}' tone.\n"

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

        _question_prompt = ""

        # Add context to prompt
        context = self.build_question_context(question=question)
        if context:
            _question_prompt += dedent(
                f"""
            Use the provided articles delimited by triple quotes to answer the following question.
            If the answer cannot be found in the articles, write "I could not find an answer."

            START OF ARTICLES
            ```
            {context}
            ```
            END OF ARTICLES
            """
            )
        else:
            _question_prompt += "Answer the following question:\n"
        # Add question to prompt
        _question_prompt += f"\nQuestion: {question}\n"

        # Add chat history to prompt
        chat_history = self.build_chat_history()
        if chat_history:
            _question_prompt += dedent(
                f"""
            You have access to the following chat history which you can use to answer the question if it helps.
            START OF CHAT HISTORY
            {chat_history}
            END OF CHAT HISTORY
            """
            )

        return dedent(_question_prompt)

    def review(self, question: str) -> Iterator[str]:
        if self.log_messages:
            logger.info(f"Reviewing: {question}")

        # Add the system prompt to llm_messages
        if len(self._llm_messages) == 0:
            self._llm_messages.append(Message(role="system", content=self.build_system_prompt()))

        # Add the question prompt to llm_messages
        self._llm_messages.append(Message(role="user", content=self.get_question_prompt(question=question)))
        if self.log_messages:
            for message in self._llm_messages:
                logger.info(f"{message.role}: {message.content}")

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

        if self.log_messages:
            logger.info(f"Response: {response}")

        # Add response to user_messages
        self._user_messages.append(Message(role="assistant", content=response))
        # Add response to llm_messages
        self._llm_messages.append(Message(role="assistant", content=response))
        # Add response tokens to usage data
        if "response_tokens" in self.usage_data:
            self.usage_data["response_tokens"] += response_tokens
        else:
            self.usage_data["response_tokens"] = response_tokens
