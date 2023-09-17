from datetime import datetime
from typing import List, Any, Optional, Dict, Iterator, Callable, cast, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from phi.conversation.history.base import ConversationHistory
from phi.conversation.schemas import ConversationRow
from phi.conversation.storage.base import ConversationStorage
from phi.document import Document
from phi.knowledge.base import KnowledgeBase
from phi.llm.base import LLM
from phi.llm.openai import OpenAIChat
from phi.llm.schemas import Message, References
from phi.llm.function.registry import FunctionRegistry
from phi.utils.format_str import remove_indent
from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.timer import Timer


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
    # If there is no database, this is set to a unique 16 digit integer.
    id: Optional[int] = None
    # Conversation name
    name: Optional[str] = None
    # Conversation type. Eg RAG, AUTO, etc.
    type: Optional[str] = None
    # Conversation tags
    tags: Optional[List[str]] = None
    # True if this conversation is active i.e. not ended
    is_active: bool = True
    # Set log level to debug
    debug_logs: bool = False
    # Monitor conversations on phidata.com
    monitor: bool = False
    # Extra data
    extra_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this conversation was created in the database
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated in the database
    updated_at: Optional[datetime] = None

    # -*- Conversation history
    history: ConversationHistory = ConversationHistory()
    # Add history to the prompt
    add_history_to_prompt: bool = False
    add_history_to_messages: bool = False
    num_history_messages: int = 8

    # -*- Conversation Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None
    add_references_to_prompt: bool = False

    # -*- Conversation Storage
    storage: Optional[ConversationStorage] = None
    # Create table if it doesn't exist
    create_storage: bool = True
    # Conversation row from the database
    conversation_row: Optional[ConversationRow] = None

    # -*- Enable Function Calls
    function_calls: bool = False
    default_functions: bool = True
    show_function_calls: bool = False
    functions: Optional[List[Callable]] = None
    function_registries: Optional[List[FunctionRegistry]] = None

    # Function to build references for the user prompt
    # Signature:
    # def references(conversation: Conversation, question: str) -> Optional[str]:
    #    ...
    references_function: Optional[Callable[..., Optional[str]]] = None
    # Function to build the chat history for the user prompt
    # Signature:
    # def chat_history(conversation: Conversation) -> str:
    #    ...
    chat_history_function: Optional[Callable[..., Optional[str]]] = None
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
    user_prompt_function: Optional[Callable[..., str]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("debug_logs", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @model_validator(mode="after")  # type: ignore
    def set_llm_functions(self) -> "Conversation":
        if self.function_calls:
            if self.default_functions:
                default_func_list: List[Callable] = [
                    self.get_last_n_chats,
                    self.search_knowledge_base,
                ]
                for func in default_func_list:
                    self.llm.add_function(func)

            # Add functions from self.functions
            if self.functions is not None:
                for func in self.functions:
                    self.llm.add_function(func)

            # Add functions from registries
            if self.function_registries is not None:
                for registry in self.function_registries:
                    self.llm.add_function_registry(registry)

            # Set function call to auto if it is not set
            if self.llm.function_call is None:
                self.llm.function_call = "auto"

            # Set show_function_calls if it is not set on the llm
            if self.llm.show_function_calls is None:
                self.llm.show_function_calls = self.show_function_calls
        return self  # type: ignore

    @model_validator(mode="after")
    def set_id(self) -> "Conversation":
        if self.storage is None:
            import random

            # Generate random integer ID
            self.id = random.randint(1000000000000000, 9999999999999999)
            logger.debug(f"Conversation ID set to {self.id}")
        return self

    def to_conversation_row(self) -> ConversationRow:
        """Create a ConversationRow for the current conversation (usually to save to the database)"""

        return ConversationRow(
            id=self.id,
            name=self.name,
            user_name=self.user_name,
            user_persona=self.user_persona,
            is_active=self.is_active,
            llm=self.llm.to_dict(),
            history=self.history.to_dict(),
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
            if self.create_storage:
                self.storage.create()
            self.conversation_row = self.storage.upsert(conversation=self.to_conversation_row())
            if self.id is None and self.conversation_row is not None:
                self.id = self.conversation_row.id
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
                # TODO: Add introduction through a separate function
                if self.introduction is not None:
                    self.history.add_chat_history([Message(role="assistant", content=self.introduction)])
                self.conversation_row = self.write_to_storage()
                if self.conversation_row is None:
                    raise Exception("Failed to create conversation")
                logger.debug(f"Created conversation: {self.conversation_row.id}")
                self.from_conversation_row(row=self.conversation_row)
                self._api_upsert_conversation()

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

        _system_prompt = "You are a chatbot "

        if self.user_persona:
            _system_prompt += f"that is designed to help a '{self.user_persona}' with their work.\n"
        else:
            _system_prompt += "that is designed to help a user with their work.\n"

        if self.knowledge_base is not None:
            _system_prompt += "You have access to a knowledge base that you can search for information.\n"
            _system_prompt += (
                "If you cannot find the answer in the knowledge base, "
                "say that you cannot find the answer in the knowledge base.\n"
            )

        _system_prompt += "If you don't know the answer, say 'I don't know'"

        # Return the system prompt after removing newlines and indenting
        _system_prompt = cast(str, remove_indent(_system_prompt))
        return _system_prompt

    def get_references(self, query: str) -> Optional[str]:
        """Return relevant information from the knowledge base"""

        if self.references_function is not None:
            reference_kwargs = {"query": query, "conversation": self}
            return remove_indent(self.references_function(**reference_kwargs))

        if self.knowledge_base is None:
            return None

        import json

        relevant_docs: List[Document] = self.knowledge_base.search(query=query)
        return json.dumps([doc.to_dict() for doc in relevant_docs])

    def get_formatted_chat_history(self) -> Optional[str]:
        """Returns a formatted chat history to use in the user prompt"""

        if self.chat_history_function is not None:
            chat_history_kwargs = {"conversation": self}
            return remove_indent(self.chat_history_function(**chat_history_kwargs))

        formatted_history = self.history.get_formatted_history(last_n=self.num_history_messages)
        if formatted_history == "":
            return None
        return remove_indent(formatted_history)

    def get_user_prompt(
        self, message: str, references: Optional[str] = None, chat_history: Optional[str] = None
    ) -> str:
        """Build the user prompt given a message, references and chat_history"""

        if self.user_prompt_function is not None:
            user_prompt_kwargs = {
                "references": references,
                "chat_history": chat_history,
                "conversation": self,
            }
            _user_prompt_from_function = remove_indent(self.user_prompt_function(message=message, **user_prompt_kwargs))
            if _user_prompt_from_function is not None:
                return _user_prompt_from_function
            else:
                raise Exception("User prompt function returned None")

        _user_prompt = "Your task is to respond to the following message"
        if self.user_persona:
            _user_prompt += f" from a '{self.user_persona}'"
        # Add question to the prompt
        _user_prompt += f":\nUSER: {message}"

        # Add references to prompt
        if references:
            _user_prompt += f"""\n
                You can use the following information from the knowledge base if it helps respond to the message.
                START OF KNOWLEDGE BASE INFORMATION
                ```
                {references}
                ```
                END OF KNOWLEDGE BASE INFORMATION
                """

        # Add chat_history to prompt
        if chat_history:
            _user_prompt += f"""\n
                You can use the following chat history to reference past messages.
                START OF CHAT HISTORY
                ```
                {chat_history}
                ```
                END OF CHAT HISTORY
                """

        if references or chat_history:
            _user_prompt += "\nRemember, your task is to respond to the following message in the best way possible."
            _user_prompt += f"\nUSER: {message}"
        _user_prompt += "\nASSISTANT: "

        # Return the user prompt after removing newlines and indenting
        _user_prompt = cast(str, remove_indent(_user_prompt))
        return _user_prompt

    def _chat(self, message: str, stream: bool = True) -> Iterator[str]:
        logger.debug("*********** Conversation Chat Start ***********")
        # Load the conversation from the database if available
        self.read_from_storage()

        # -*- Build the system prompt
        system_prompt = self.get_system_prompt()

        # -*- References to send to the api
        references: Optional[References] = None

        # -*- Get references to add to the user prompt
        user_prompt_references = None
        if self.add_references_to_prompt:
            reference_timer = Timer()
            reference_timer.start()
            user_prompt_references = self.get_references(query=message)
            reference_timer.stop()
            references = References(
                query=message, references=user_prompt_references, time=round(reference_timer.elapsed, 4)
            )
            logger.debug(f"Time to get references: {reference_timer.elapsed:.4f}s")

        # -*- Get chat history to add to the user prompt
        user_prompt_chat_history = None
        if self.add_history_to_prompt:
            user_prompt_chat_history = self.get_formatted_chat_history()

        # -*- Build the user prompt
        user_prompt = self.get_user_prompt(
            message=message, references=user_prompt_references, chat_history=user_prompt_chat_history
        )

        # -*- Build messages to send to the LLM
        # Create system message
        system_prompt_message = Message(role="system", content=system_prompt)
        # Create user message
        user_prompt_message = Message(role="user", content=user_prompt)
        # Create message list
        messages: List[Message] = [system_prompt_message]
        if self.add_history_to_messages:
            messages += self.history.get_last_n_messages(last_n=self.num_history_messages)
        messages += [user_prompt_message]

        # -*- Generate response
        llm_response = ""
        if stream:
            for response_chunk in self.llm.response_stream(messages=messages):
                llm_response += response_chunk
                yield response_chunk
        else:
            llm_response = self.llm.response(messages=messages)

        # -*- Add messages to the history
        # Add the system prompt to the history - added only if this is the first message to the LLM
        self.history.add_system_prompt(message=system_prompt_message)

        # Add user message to the history - this is added to the chat history
        self.history.add_user_message(message=Message(role="user", content=message))

        # Add user prompt to the history - this is added to the llm history
        self.history.add_user_prompt(message=user_prompt_message)

        # Add references to the history
        if references:
            self.history.add_references(references=references)

        # Add llm response to the history - this is added to the chat and llm history
        self.history.add_llm_response(message=Message(role="assistant", content=llm_response))

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Send conversation event
        event_data = {
            "user_message": message,
            "llm_response": llm_response,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "references": references.model_dump(exclude_none=True) if references else None,
            "metrics": self.llm.metrics,
        }
        self._api_send_conversation_event(event_type="chat", event_data=event_data)

        # -*- Return final response if not streaming
        if not stream:
            yield llm_response
        logger.debug("*********** Conversation Chat End ***********")

    def chat(self, message: str, stream: bool = True) -> Union[Iterator[str], str]:
        resp = self._chat(message=message, stream=stream)
        if stream:
            return resp
        else:
            return next(resp)

    def _prompt(
        self, messages: List[Message], user_message: Optional[str] = None, stream: bool = True
    ) -> Iterator[str]:
        logger.debug("*********** Conversation Prompt Start ***********")
        # Load the conversation from the database if available
        self.read_from_storage()

        # -*- Add user message to the history - this is added to the chat history
        if user_message:
            self.history.add_user_message(Message(role="user", content=user_message))

        # -*- Add prompts to the history - these are added to the llm history
        for message in messages:
            self.history.add_user_prompt(message=message)

        # -*- Generate response
        llm_response = ""
        if stream:
            for response_chunk in self.llm.response_stream(messages=messages):
                llm_response += response_chunk
                yield response_chunk
        else:
            llm_response = self.llm.response(messages=messages)

        # -*- Add response to the history - this is added to the chat and llm history
        self.history.add_llm_response(Message(role="assistant", content=llm_response))

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Send conversation event
        event_data = {
            "user_message": user_message,
            "llm_response": llm_response,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "metrics": self.llm.metrics,
        }
        self._api_send_conversation_event(event_type="prompt", event_data=event_data)

        # -*- Return final response if not streaming
        if not stream:
            yield llm_response
        logger.debug("*********** Conversation Prompt End ***********")

    def prompt(
        self, messages: List[Message], user_message: Optional[str] = None, stream: bool = True
    ) -> Union[Iterator[str], str]:
        resp = self._prompt(messages=messages, user_message=user_message, stream=stream)
        if stream:
            return resp
        else:
            return next(resp)

    def rename(self, name: str) -> None:
        """Rename the conversation"""
        self.read_from_storage()
        self.name = name

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Update conversation
        self._api_upsert_conversation()

    def generate_name(self) -> str:
        """Generate a name for the conversation using chat history"""
        _conv = (
            "Please provide a suitable name for the following conversation in maximum 5 words.\n"
            "Remember, do not exceed 5 words.\n\n"
        )
        for message in self.history.chat_history[1:6]:
            _conv += f"{message.role.upper()}: {message.content}\n"

        _conv += "\n\nConversation Name:"

        system_message = Message(
            role="system",
            content="Please provide a suitable name for the following conversation in maximum 5 words.",
        )
        user_message = Message(role="user", content=_conv)
        generate_name_message = [system_message, user_message]
        generated_name = self.llm.response(messages=generate_name_message)
        if len(generated_name.split()) > 15:
            logger.error("Generated name is too long. Trying again.")
            return self.generate_name()
        return generated_name.replace('"', "").strip()

    def auto_rename(self) -> None:
        """Automatically rename the conversation"""
        self.read_from_storage()
        generated_name = self.generate_name()
        logger.debug(f"Generated name: {generated_name}")
        self.name = generated_name

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Update conversation
        self._api_upsert_conversation()

    ###########################################################################
    # Api functions
    ###########################################################################

    def _api_upsert_conversation(self):
        if not self.monitor:
            return

        from phi.api.conversation import upsert_conversation, ConversationUpdate

        logger.debug("Sending conversation event")
        try:
            conversation_row: ConversationRow = self.conversation_row or self.to_conversation_row()
            upsert_conversation(
                conversation=ConversationUpdate(
                    conversation_key=conversation_row.conversation_key(),
                    conversation_data=conversation_row.conversation_data(),
                ),
            )
        except Exception as e:
            logger.debug(f"Could not log conversation event: {e}")

    def _api_send_conversation_event(
        self, event_type: str = "chat", event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        if not self.monitor:
            return

        from phi.api.conversation import log_conversation_event, ConversationEventCreate

        logger.debug("Sending conversation event")
        try:
            conversation_row: ConversationRow = self.conversation_row or self.to_conversation_row()
            log_conversation_event(
                conversation=ConversationEventCreate(
                    conversation_key=conversation_row.conversation_key(),
                    conversation_data=conversation_row.conversation_data(),
                    event_type=event_type,
                    event_data=event_data,
                ),
            )
        except Exception as e:
            logger.debug(f"Could not log conversation event: {e}")

    ###########################################################################
    # LLM functions
    ###########################################################################

    def get_last_n_chats(self, num_chats: Optional[int] = None) -> str:
        """Returns the last n chats between the user and assistant.
        Example:
            - To get the last chat, use num_chats=1.
            - To get the last 5 chats, use num_chats=5.
            - To get all chats, use num_chats=None.
            - To get the first chat, use num_chats=None and pick the first message.
        :param num_chats: The number of chats to return.
            Each chat contains 2 messages. One from the user and one from the assistant.
        :return: A list of dictionaries representing the chat history.
        """
        import json

        history: List[Dict[str, Any]] = []
        all_chats = self.history.get_chats()
        if len(all_chats) == 0:
            return ""

        chats_added = 0
        for chat in all_chats[::-1]:
            history.insert(0, chat[1].to_dict())
            history.insert(0, chat[0].to_dict())
            chats_added += 1
            if num_chats is not None and chats_added >= num_chats:
                break
        return json.dumps(history)

    def search_knowledge_base(self, query: str) -> Optional[str]:
        """Search the knowledge base for information about a users query.

        :param query: The query to search for.
        :return: A string containing the response from the knowledge base.
        """
        return self.get_references(query=query)

    ###########################################################################
    # Print Response
    ###########################################################################

    def print_response(self, message: str, stream: bool = True) -> None:
        from phi.cli.console import console
        from rich.live import Live
        from rich.table import Table
        from rich.markdown import Markdown

        if stream:
            response = ""
            with Live() as live_log:
                for resp in self.chat(message, stream=True):
                    response += resp

                    table = Table()
                    table.add_column("Message")
                    table.add_column(message)
                    md_response = Markdown(response)
                    table.add_row("Response", md_response)
                    live_log.update(table)
        else:
            response = self.chat(message, stream=False)  # type: ignore
            md_response = Markdown(response)
            table = Table()
            table.add_column("Message")
            table.add_column(message)
            table.add_row("Response", md_response)
            console.print(table)
