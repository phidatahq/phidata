from datetime import datetime
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
from phi.utils.timer import Timer
from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.format_str import remove_indent


class Conversation(BaseModel):
    # -*- LLM settings
    llm: LLM = OpenAIChat()
    # System prompt
    system_prompt: Optional[str] = None
    # Add an initial introduction (from the assistant) to the chat history
    introduction: Optional[str] = None

    # -*- User settings
    # Name of the user participating in this conversation.
    user_name: Optional[str] = None
    user_persona: Optional[str] = None

    # -*- Conversation settings
    # Database ID/Primary key for this conversation.
    # This is set after the conversation is started and saved to the database.
    id: Optional[int] = None
    # Conversation name
    name: Optional[str] = None
    # True if this conversation is active i.e. not ended
    is_active: bool = True
    # Set log level to debug
    debug_logs: bool = False
    # Monitor conversations on phidata.com
    monitoring: bool = False
    # Extra data
    extra_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this conversation was created in the database
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated in the database
    updated_at: Optional[datetime] = None

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
    create_storage: bool = True
    # Conversation row from the database
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

    def to_conversation_row(self) -> ConversationRow:
        """Create a ConversationRow for the current conversation (usually to save to the database)"""

        return ConversationRow(
            id=self.id,
            name=self.name,
            user_name=self.user_name,
            user_persona=self.user_persona,
            is_active=self.is_active,
            llm=self.llm.model_dump(exclude_none=True),
            history=self.history.model_dump(include={"chat_history", "llm_history", "references"}),
            extra_data=self.extra_data,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def from_conversation_row(self, row: ConversationRow):
        """Load the existing conversation from a ConversationRow (usually from the database)"""

        # Values that are overwritten from the ConversationRow if they are not set in the conversation
        if self.id is None and row.id is not None:
            self.id = row.id
        if self.name is None and row.name is not None:
            self.name = row.name
        if self.user_name is None and row.user_name is not None:
            self.user_name = row.user_name
        if self.user_persona is None and row.user_persona is not None:
            self.user_persona = row.user_persona
        if self.is_active is None and row.is_active is not None:
            self.is_active = row.is_active

        # Update llm metrics from the ConversationRow
        if row.llm is not None:
            llm_metrics = row.llm.get("metrics")
            if llm_metrics is not None and isinstance(llm_metrics, dict):
                try:
                    self.llm.metrics = llm_metrics
                except Exception as e:
                    logger.error(f"Failed to load llm metrics: {e}")

        # Update conversation history from the ConversationRow
        if row.history is not None:
            try:
                self.history = self.history.__class__.model_validate(row.history)
            except Exception as e:
                logger.error(f"Failed to load conversation history: {e}")

        # Update extra data from the ConversationRow
        if row.extra_data is not None:
            # If extra data is set in the conversation,
            # merge it with the database extra data. The conversation extra data takes precedence
            if self.extra_data is not None and row.extra_data is not None:
                self.extra_data = {**row.extra_data, **self.extra_data}
            # If extra data is not set in the conversation, use the database extra data
            if self.extra_data is None and row.extra_data is not None:
                self.extra_data = row.extra_data

        # Update the timestamp of when this conversation was created in the database
        if row.created_at is not None:
            self.created_at = row.created_at

        # Update the timestamp of when this conversation was last updated in the database
        if row.updated_at is not None:
            self.updated_at = row.updated_at

    def read_from_storage(self) -> Optional[ConversationRow]:
        """Load the conversation from storage"""
        if self.storage is not None and self.id is not None:
            self.conversation_row = self.storage.read(conversation_id=self.id)
            if self.conversation_row is not None:
                logger.debug(f"Found conversation: {self.conversation_row.id}")
                self.from_conversation_row(row=self.conversation_row)
                logger.debug(f"Loaded conversation: {self.id}")
        return self.conversation_row

    def write_to_storage(self) -> Optional[ConversationRow]:
        """Save the conversation to the storage"""
        if self.storage is not None:
            self.conversation_row = self.storage.upsert(conversation=self.to_conversation_row())
        return self.conversation_row

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
                self.read_from_storage()

            # If the conversation ID is not available
            # OR the conversation is not found in the database
            # create a new conversation in the database
            if self.conversation_row is None:
                logger.debug("Creating new conversation")
                if self.create_storage:
                    self.storage.create()
                if self.introduction is not None:
                    self.history.add_chat_history([Message(role="assistant", content=self.introduction)])
                self.conversation_row = self.write_to_storage()
                if self.conversation_row is None:
                    raise Exception("Failed to create conversation")
                logger.debug(f"Created conversation: {self.conversation_row.id}")
                self.from_conversation_row(row=self.conversation_row)

        return self.id

    def end(self) -> None:
        """End the conversation"""
        if self.storage is not None and self.id is not None:
            self.storage.end(conversation_id=self.id)
        self.is_active = False

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

    def review(self, question: str, stream: bool = True) -> Iterator[str]:
        logger.debug(f"Reviewing: {question}")

        # Load the conversation from the database if available
        self.read_from_storage()

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
        if stream:
            response = ""
            for delta in self.llm.response_stream(messages=[m.model_dump(exclude_none=True) for m in messages]):
                response += delta
                yield response
        else:
            response = self.llm.response(messages=[m.model_dump(exclude_none=True) for m in messages])
            yield response

        logger.debug(f"Response: {response}")

        # Add response to the history - this is added to the chat and llm history
        self.history.add_llm_response(message=Message(role="assistant", content=response))

        # Save conversation to storage
        self.write_to_storage()

    def chat(self, question: str, stream: bool = True, stream_delta: bool = False) -> Iterator[str]:
        logger.debug(f"Answering: {question}")

        # Load the conversation from the database if available
        self.read_from_storage()

        # -*- Build the system prompt
        system_prompt = self.get_system_prompt()

        # -*- Get references to add to the user prompt
        reference_timer = Timer()
        reference_timer.start()
        references = self.get_references(question=question)
        reference_timer.stop()
        logger.debug(f"Time to get references: {reference_timer.elapsed:.4f}s")

        # -*- Get chat history to add to the user prompt
        chat_history = self.get_chat_history() if self.add_history_to_prompt else None

        # -*- Build the user prompt
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

        # -*- Log messages for debugging
        for message in messages:
            logger.debug(f"{message.role.upper()}: {message.content}")

        # -*- Generate response
        response_timer = Timer()
        response_timer.start()
        if stream:
            llm_response = ""
            for delta in self.llm.response_stream(messages=[m.model_dump(exclude_none=True) for m in messages]):
                llm_response += delta
                if stream_delta:
                    yield delta
                else:
                    yield llm_response
        else:
            llm_response = self.llm.response(messages=[m.model_dump(exclude_none=True) for m in messages])
            yield llm_response
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Add messages to the history
        # Add the system prompt to the history - added only if this is the first message to the LLM
        self.history.add_system_prompt(message=system_message)
        # Add user question to the history - this is added to the chat history
        self.history.add_user_question(message=Message(role="user", content=question))
        # Add user prompt to the history - this is added to the llm history
        self.history.add_user_prompt(message=user_message)
        # Add references to the history
        if references:
            self.history.add_references(
                references=References(question=question, references=references, perf=round(reference_timer.elapsed, 4))
            )
        # Add response to the history - this is added to the chat and llm history
        self.history.add_llm_response(
            message=Message(role="assistant", content=llm_response, perf=round(response_timer.elapsed, 4))
        )

        # -*- Log response for debugging
        logger.debug(f"Response: {llm_response}")

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Monitor chat
        self.monitor_chat()

    def prompt(self, messages: List[Message], user_question: Optional[str] = None) -> Iterator[str]:
        logger.debug("Sending prompt request")

        # If needed, load the conversation from the database
        self.read_from_storage()

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
        for delta in self.llm.response_stream(messages=[m.model_dump(exclude_none=True) for m in messages]):
            response += delta
            yield response

        logger.debug(f"Response: {response}")

        # Add response to the history - this is added to the chat and llm history
        self.history.add_llm_response(message=Message(role="assistant", content=response))

        # Save conversation to storage
        self.write_to_storage()

    def rename(self, name: str) -> None:
        """Rename the conversation"""
        self.read_from_storage()
        self.name = name
        self.write_to_storage()

    def generate_name(self) -> str:
        """Generate a name for the conversation using chat history"""
        _conv = ""
        for message in self.history.chat_history[1:4]:
            _conv += f"{message.role.upper()}: {message.content}\n"

        system_message = Message(
            role="system",
            content="Please provide a suitable name for the conversation in maximum 5 words.",
        )
        user_message = Message(role="user", content=_conv)
        generate_name_message = [system_message, user_message]
        generate_name = self.llm.response(messages=[m.model_dump(exclude_none=True) for m in generate_name_message])
        return generate_name.replace('"', "").strip()

    def auto_rename(self) -> None:
        """Automatically rename the conversation"""
        self.read_from_storage()
        generated_name = self.generate_name()
        logger.debug(f"Generated name: {generated_name}")
        self.name = generated_name
        self.write_to_storage()

    def monitor_chat(self):
        from os import getenv
        from phi.api.conversation import log_conversation_event, ConversationEventCreate, ConversationWorkspace
        from phi.constants import WORKSPACE_ID_ENV_VAR, WORKSPACE_HASH_ENV_VAR
        from phi.utils.common import str_to_int

        logger.debug("Sending conversation event")
        try:
            workspace_id = str_to_int(getenv(WORKSPACE_ID_ENV_VAR))
            if workspace_id is None:
                logger.debug(f"Could not log conversation. {WORKSPACE_ID_ENV_VAR} invalid: {workspace_id}")
                return

            workspace_hash = getenv(WORKSPACE_HASH_ENV_VAR)
            conversation_row: ConversationRow = self.conversation_row or self.to_conversation_row()
            conversation_data = conversation_row.model_dump(
                include={"id", "name", "user_name", "user_persona", "is_active", "extra_data"}
            )

            log_conversation_event(
                conversation=ConversationEventCreate(
                    conversation_key=str(self.id),
                    conversation_data=conversation_data,
                    event_type="chat",
                    event_data=conversation_row.serializable_dict(),
                ),
                workspace=ConversationWorkspace(id_workspace=workspace_id, ws_hash=workspace_hash),
            )
        except Exception as e:
            logger.debug(f"Could not log conversation event: {e}")
