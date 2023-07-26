from typing import List, Any, Optional, Dict, Iterator, Callable, cast

from pydantic import BaseModel, ConfigDict, field_validator

from phi.document import Document
from phi.llm.base import LLM
from phi.llm.schemas import Message, References
from phi.llm.conversation.schemas import ConversationRow
from phi.llm.conversation.storage.base import ConversationStorage
from phi.llm.history.base import LLMHistory
from phi.llm.history.simple import SimpleConversationHistory
from phi.llm.knowledge.base import LLMKnowledgeBase
from phi.llm.openai import OpenAIChat
from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.format_str import remove_indent


class Conversation(BaseModel):
    # -*- LLM settings
    llm: LLM = OpenAIChat()
    # System prompt
    system_prompt: Optional[str] = None

    # -*- User settings
    # Name of the user participating in this conversation.
    user_name: Optional[str] = "anonymous"
    user_persona: Optional[str] = None

    # -*- Conversation settings
    # Database ID/Primary key for this conversation.
    # This is set after the conversation is started and saved to the database.
    id: Optional[int] = None
    # Set log level to debug
    debug_logs: bool = False
    # Monitor conversations on phidata.com
    monitoring: bool = False
    # Usage data
    usage_data: Dict[str, Any] = {}
    # Extra data
    extra_data: Optional[Dict[str, Any]] = None

    # -*- Conversation history
    history: LLMHistory = SimpleConversationHistory()
    # Add history to the prompt
    add_history_to_prompt: bool = True
    add_history_to_messages: bool = False

    # -*- Conversation Knowledge Base
    knowledge_base: Optional[LLMKnowledgeBase] = None

    # -*- Conversation Storage
    storage: Optional[ConversationStorage] = None
    # Create table if it doesn't exist
    create_storage: bool = False
    # Conversation row in the database
    conversation_row: Optional[ConversationRow] = None

    # Function to build references for the user prompt
    # Signature:
    # def references(conversation: Conversation, question: str) -> Optional[str]:
    #    ...
    references_function: Optional[Callable[["Conversation", str], Optional[str]]] = None
    # Function to build the chat history for the user prompt
    # Signature:
    # def chat_history(conversation: Conversation) -> str:
    #    ...
    chat_history_function: Optional[Callable[["Conversation"], Optional[str]]] = None
    # Functions to build the user prompt
    # Uses the references function to get references
    # Signature:
    # def student_user_prompt(
    #     conversation: Conversation,
    #     question: str,
    #     references: Optional[str] = None,
    #     chat_history: Optional[str] = None,
    # ) -> str:
    #     """Build the user prompt for a student given a question, references and chat_history"""
    #     ...
    user_prompt_function: Optional[Callable[["Conversation", str, Optional[str], Optional[str]], str]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_logs", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    def get_database_row(self) -> ConversationRow:
        """Return the conversation row"""

        return ConversationRow(
            id=self.id,
            user_name=self.user_name,
            user_persona=self.user_persona,
            is_active=True,
            llm={
                "type": self.llm.__class__.__name__,
                "config": self.llm.model_dump(exclude_none=True),
            },
            history=self.history.model_dump(include={"chat_history", "llm_history", "references"}),
            usage_data=self.usage_data,
            extra_data=self.extra_data,
            created_at=None,
            updated_at=None,
        )

    def from_database_row(self, conversation_row: ConversationRow):
        """Use the data to build the conversation

        Note:
            - Only id, history and usage_data are updated from the database.
            - LLM data, user_name, user_persona, is_active, extra_data are not updated from the database
        """

        # Values that should be overwritten from the database
        if self.id is None and conversation_row.id is not None:
            self.id = conversation_row.id

        # Update conversation history from database
        if conversation_row.history is not None:
            try:
                self.history = self.history.__class__.model_validate(conversation_row.history)
            except Exception as e:
                logger.error(f"Failed to load conversation history: {e}")

        # Update usage data from database
        if conversation_row.usage_data is not None:
            self.usage_data = conversation_row.usage_data

    def start(self) -> Optional[int]:
        """Starts the conversation and returns the conversation ID
        that can be used to retrieve this conversation later.
        """

        # If the conversation is already started, return the conversation ID
        if self.conversation_row is not None:
            return self.conversation_row.id

        if self.storage is not None:
            # If the conversation ID is available, read the conversation from the database
            if self.id is not None:
                logger.debug(f"Reading conversation: {self.id}")
                self.conversation_row = self.read_from_storage()
                if self.conversation_row is not None:
                    logger.debug(f"Conversation found: {self.id}")
                else:
                    logger.debug(f"Conversation not found: {self.id}")

            # If the conversation ID is not available OR the conversation is not found in the database,
            # create a new conversation in the database
            if self.conversation_row is None:
                logger.debug("Creating new conversation")
                if self.create_storage:
                    self.storage.create()
                self.conversation_row = self.save_to_storage()
                if self.conversation_row is None:
                    raise Exception("Failed to create conversation")
                logger.debug(f"Created conversation: {self.conversation_row.id}")

        if self.conversation_row is not None:
            self.from_database_row(self.conversation_row)
            return self.conversation_row.id

        return None

    def get_system_prompt(self) -> str:
        """Return the system prompt for the conversation"""

        if self.system_prompt:
            return "\n".join([line.strip() for line in self.system_prompt.split("\n")])

        _system_prompt = ""
        if self.llm.name:
            _system_prompt += f"You are a chatbot named '{self.llm.name}'"
        else:
            _system_prompt += "You are a chatbot "

        if self.user_persona:
            _system_prompt += f"that is designed to help a '{self.user_persona}' with their work.\n"
        else:
            _system_prompt += "that is designed to help a user with their work.\n"

        _system_prompt += "If you don't know the answer, say 'I don't know'. You can ask follow up questions if needed."

        # Return the system prompt after removing newlines and indenting
        _system_prompt = cast(str, remove_indent(_system_prompt))
        return _system_prompt

    def get_references(self, question: str) -> Optional[str]:
        """Return relevant information from the knowledge base"""

        if self.references_function is not None:
            return remove_indent(self.references_function(self, question))

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

    def get_chat_history(self) -> Optional[str]:
        """Return the chat history to use in the user prompt"""

        if self.chat_history_function is not None:
            return remove_indent(self.chat_history_function(self))

        return remove_indent(self.history.get_formatted_history())

    def get_user_prompt(
        self, question: str, references: Optional[str] = None, chat_history: Optional[str] = None
    ) -> str:
        """Build the user prompt given a question, references and chat_history"""

        if self.user_prompt_function is not None:
            _user_prompt_from_function = remove_indent(
                self.user_prompt_function(self, question, references, chat_history)
            )
            if _user_prompt_from_function is not None:
                return _user_prompt_from_function
            else:
                raise Exception("User prompt function returned None")

        _user_prompt = "Your task is to answer the following question"
        if self.user_persona:
            _user_prompt += f" for a '{self.user_persona}'"
        # Add question to the prompt
        _user_prompt += f":\nQuestion: {question}\n"

        # Add references to prompt
        if references:
            _user_prompt += f"""
                You can use the following information if it helps answer the question.

                START OF INFORMATION
                ```
                {references}
                ```
                END OF INFORMATION
                """

        # Add chat_history to prompt
        if chat_history:
            _user_prompt += f"""
                You can use the following chat history to reference previous questions and answers.

                START OF CHAT HISTORY
                ```
                {chat_history}
                ```
                END OF CHAT HISTORY
                """

        _user_prompt += "\nRemember, your task is to answer the following question:"
        _user_prompt += f"\nQuestion: {question}"
        _user_prompt += "\nAnswer: "

        # Return the user prompt after removing newlines and indenting
        _user_prompt = cast(str, remove_indent(_user_prompt))
        return _user_prompt

    def add_introduction(self, introduction: str) -> None:
        """Add the introduction to the chat history"""
        self.history.add_chat_history([Message(role="assistant", content=introduction)])
        self.save_to_storage()

    def review(self, question: str) -> Iterator[str]:
        logger.debug(f"Reviewing: {question}")

        # -*- Build the system prompt
        system_prompt = self.get_system_prompt()

        # -*- Build the user prompt
        references = self.get_references(question=question)
        chat_history = self.get_chat_history() if self.add_history_to_prompt else None
        user_prompt = self.get_user_prompt(question=question, references=references, chat_history=chat_history)

        # -*- Build messages to send to the LLM
        # Create system message
        system_message = Message(role="system", content=system_prompt)
        # Create user message
        user_message = Message(role="user", content=user_prompt)
        # Create message list
        messages: List[Message] = [system_message]
        if self.add_history_to_messages:
            messages += self.history.chat_history
        messages += [user_message]

        # Add messages to the history
        # Add the system prompt to the history - added only if this is the first message to the LLM
        self.history.add_system_prompt(message=system_message)
        # Add user question to the history - this is added to the chat history
        self.history.add_user_question(message=Message(role="user", content=question))
        # Add user prompt to the history - this is added to the llm history
        self.history.add_user_prompt(message=user_message)
        # Add references to the history
        if references:
            self.history.add_references(references=References(question=question, references=references))

        # Log messages
        for message in messages:
            logger.debug(f"{message.role.upper()}: {message.content}")

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

        # Monitor conversation
        self.monitor()

    def prompt(self, messages: List[Message], user_question: Optional[str] = None) -> Iterator[str]:
        logger.debug("Sending prompt request")

        # Add user question to the history - this is added to the chat history
        if user_question:
            self.history.add_user_question(message=Message(role="user", content=user_question))

        # Add user prompts to the history - these are added to the llm history
        for message in messages:
            self.history.add_user_prompt(message=message)
            # Log messages
            logger.debug(f"{message.role.upper()}: {message.content}")

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

        # Monitor conversation
        self.monitor()

    def read_from_storage(self) -> Optional[ConversationRow]:
        """Read the conversation from the storage"""
        if self.storage is not None and self.id is not None:
            return self.storage.read(conversation_id=self.id)
        return None

    def save_to_storage(self) -> Optional[ConversationRow]:
        """Save the conversation to the storage"""
        if self.storage is not None:
            return self.storage.upsert(conversation=self.get_database_row())
        return None

    def end(self) -> None:
        """End the conversation"""
        if self.storage is not None and self.id is not None:
            self.storage.end(conversation_id=self.id)

    def monitor(self):
        logger.debug("Sending monitoring request")
        pass
