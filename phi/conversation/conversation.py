import json
from uuid import uuid4
from datetime import datetime
from typing import List, Any, Optional, Dict, Iterator, Callable, cast, Union, Type, Tuple

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field, ValidationError

from phi.conversation.row import ConversationRow
from phi.document import Document
from phi.knowledge.base import KnowledgeBase
from phi.llm.base import LLM
from phi.llm.openai import OpenAIChat
from phi.llm.message import Message
from phi.llm.references import References
from phi.memory.conversation import ConversationMemory
from phi.storage.conversation import ConversationStorage
from phi.task.task import Task
from phi.task.llm import LLMTask
from phi.tools import Tool, ToolRegistry
from phi.utils.format_str import remove_indent
from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.timer import Timer


class Conversation(BaseModel):
    # -*- LLM settings
    llm: LLM = OpenAIChat()
    # Add an introduction (from the LLM) to the chat history
    introduction: Optional[str] = None

    # -*- User settings
    # Name and type of user participating in this conversation.
    user_name: Optional[str] = None
    user_type: Optional[str] = None

    # -*- Conversation settings
    # Conversation UUID
    id: Optional[str] = Field(None, validate_default=True)
    # Conversation name
    name: Optional[str] = None
    # True if this conversation is active i.e. not ended
    is_active: bool = True
    # Metadata associated with this conversation
    meta_data: Optional[Dict[str, Any]] = None
    # Extra data associated with this conversation
    extra_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this conversation was created in the database
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated in the database
    updated_at: Optional[datetime] = None

    # -*- Conversation Memory
    memory: ConversationMemory = ConversationMemory()
    # Add chat history to the prompt sent to the LLM.
    # If True, a formatted chat history is added to the default user_prompt.
    add_chat_history_to_prompt: bool = False
    # Add chat history to the messages sent to the LLM.
    # If True, the chat history is added to the messages sent to the LLM.
    add_chat_history_to_messages: bool = False
    # Number of previous messages to add to prompt or messages sent to the LLM.
    num_history_messages: int = 6

    # -*- Conversation Storage
    storage: Optional[ConversationStorage] = None
    # Create table if it doesn't exist
    create_storage: bool = True
    # ConversationRow from the database: DO NOT SET THIS MANUALLY
    database_row: Optional[ConversationRow] = None

    # -*- Conversation Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None
    # Add references from the knowledge base to the prompt sent to the LLM.
    add_references_to_prompt: bool = False

    # -*- Enable Function Calls
    # Makes the conversation Autonomous by letting the LLM call functions to achieve tasks.
    function_calls: bool = False
    # Add default functions to the LLM when function_calls is True.
    default_functions: bool = True
    # Show function calls in LLM messages.
    show_function_calls: bool = False
    # Maximum number of function calls allowed.
    function_call_limit: Optional[int] = None

    # -*- Conversation Tools
    # A list of tools provided to the LLM.
    # Tools are functions the model may generate JSON inputs for.
    # If you provide a dict, it is not called by the model.
    tools: Optional[List[Union[Tool, ToolRegistry, Callable, Dict]]] = None
    # Controls which (if any) function is called by the model.
    # "none" means the model will not call a function and instead generates a message.
    # "auto" means the model can pick between generating a message or calling a function.
    # Specifying a particular function via {"type: "function", "function": {"name": "my_function"}}
    #   forces the model to call that function.
    # "none" is the default when no functions are present. "auto" is the default if functions are present.
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None

    # -*- Tasks
    # Generate a response using tasks instead of a prompt
    tasks: Optional[List[Task]] = None

    #
    # -*- Prompt Settings
    #
    # -*- System prompt: provide the system prompt as a string
    system_prompt: Optional[str] = None
    # -*- System prompt function: provide the system prompt as a function
    # This function is provided the conversation as an argument
    #   and should return the system_prompt as a string.
    # Signature:
    # def system_prompt_function(conversation: Conversation) -> str:
    #    ...
    system_prompt_function: Optional[Callable[..., Optional[str]]] = None
    # If True, the conversation provides a default system prompt
    use_default_system_prompt: bool = True

    # -*- User prompt: provide the user prompt as a string
    # Note: this will ignore the message provided to the chat function
    user_prompt: Optional[Union[List[Dict], str]] = None
    # -*- User prompt function: provide the user prompt as a function.
    # This function is provided the conversation and the user message as arguments
    #   and should return the user_prompt as a Union[List[Dict], str].
    # If add_references_to_prompt is True, then references are also provided as an argument.
    # If add_chat_history_to_prompt is True, then chat_history is also provided as an argument.
    # Signature:
    # def custom_user_prompt_function(
    #     conversation: Conversation,
    #     message: Union[List[Dict], str],
    #     references: Optional[str] = None,
    #     chat_history: Optional[str] = None,
    # ) -> Union[List[Dict], str]:
    #     ...
    user_prompt_function: Optional[Callable[..., str]] = None
    # If True, the conversation provides a default user prompt
    use_default_user_prompt: bool = True
    # -*- Functions to customize the user_prompt
    # Function to build references for the default user_prompt
    # This function, if provided, is called when add_references_to_prompt is True
    # Signature:
    # def references(conversation: Conversation, query: str) -> Optional[str]:
    #     ...
    references_function: Optional[Callable[..., Optional[str]]] = None
    # Function to build the chat_history for the default user prompt
    # This function, if provided, is called when add_chat_history_to_prompt is True
    # Signature:
    # def chat_history(conversation: Conversation) -> str:
    #     ...
    chat_history_function: Optional[Callable[..., Optional[str]]] = None

    # -*- Output Settings
    # Output model for the responses
    output_model: Optional[Union[str, List, Type[BaseModel]]] = None
    # Format the output using markdown
    markdown: bool = True
    # List of guidelines for the default system prompt
    guidelines: Optional[List[str]] = None
    # -*- Last LLM response i.e. the final output of this conversation
    output: Optional[Any] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("id", mode="before")
    def set_conversation_id(cls, v: Optional[str]) -> str:
        return v if v is not None else str(uuid4())

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @model_validator(mode="after")
    def add_tools_to_llm(self) -> "Conversation":
        if self.tools is not None:
            for tool in self.tools:
                self.llm.add_tool(tool)

        if self.function_calls and self.default_functions:
            if self.memory is not None:
                self.llm.add_tool(self.get_last_n_chats)
            if self.knowledge_base is not None:
                self.llm.add_tool(self.search_knowledge_base)

        # Set show_function_calls if it is not set on the llm
        if self.llm.show_function_calls is None and self.show_function_calls is not None:
            self.llm.show_function_calls = self.show_function_calls

        # Set tool_choice to auto if it is not set on the llm
        if self.llm.tool_choice is None and self.tool_choice is not None:
            self.llm.tool_choice = self.tool_choice

        # Set function_call_limit if it is less than the llm function_call_limit
        if self.function_call_limit is not None and self.function_call_limit < self.llm.function_call_limit:
            self.llm.function_call_limit = self.function_call_limit

        return self

    @model_validator(mode="after")
    def add_response_format_to_llm(self) -> "Conversation":
        if self.output_model is not None:
            if isinstance(self.llm, OpenAIChat):
                self.llm.response_format = {"type": "json_object"}
            else:
                logger.warning(f"output_model is not supported for {self.llm.__class__.__name__}")
        return self

    def to_database_row(self) -> ConversationRow:
        """Create a ConversationRow for the current conversation (to save to the database)"""

        return ConversationRow(
            id=self.id,
            name=self.name,
            user_name=self.user_name,
            user_type=self.user_type,
            is_active=self.is_active,
            llm=self.llm.to_dict(),
            memory=self.memory.to_dict(),
            meta_data=self.meta_data,
            extra_data=self.extra_data,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def from_database_row(self, row: ConversationRow):
        """Load the existing conversation from a ConversationRow (from the database)"""

        # Values that are overwritten from the database if they are not set in the conversation
        if self.id is None and row.id is not None:
            self.id = row.id
        if self.name is None and row.name is not None:
            self.name = row.name
        if self.user_name is None and row.user_name is not None:
            self.user_name = row.user_name
        if self.user_type is None and row.user_type is not None:
            self.user_type = row.user_type
        if self.is_active is None and row.is_active is not None:
            self.is_active = row.is_active

        # Update llm data from the ConversationRow
        if row.llm is not None:
            # Update llm metrics from the database
            llm_metrics_from_db = row.llm.get("metrics")
            if llm_metrics_from_db is not None and isinstance(llm_metrics_from_db, dict):
                try:
                    self.llm.metrics = llm_metrics_from_db
                except Exception as e:
                    logger.warning(f"Failed to load llm metrics: {e}")

        # Update conversation memory from the ConversationRow
        if row.memory is not None:
            try:
                self.memory = self.memory.__class__.model_validate(row.memory)
            except Exception as e:
                logger.warning(f"Failed to load conversation memory: {e}")

        # Update meta_data from the database
        if row.meta_data is not None:
            # If meta_data is set in the conversation,
            # merge it with the database meta_data. The conversation meta_data takes precedence
            if self.meta_data is not None and row.meta_data is not None:
                self.meta_data = {**row.meta_data, **self.meta_data}
            # If meta_data is not set in the conversation, use the database meta_data
            if self.meta_data is None and row.meta_data is not None:
                self.meta_data = row.meta_data

        # Update extra_data from the database
        if row.extra_data is not None:
            # If extra_data is set in the conversation,
            # merge it with the database extra_data. The conversation extra_data takes precedence
            if self.extra_data is not None and row.extra_data is not None:
                self.extra_data = {**row.extra_data, **self.extra_data}
            # If extra_data is not set in the conversation, use the database extra_data
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
            self.database_row = self.storage.read(conversation_id=self.id)
            if self.database_row is not None:
                logger.debug(f"-*- Loading conversation: {self.database_row.id}")
                self.from_database_row(row=self.database_row)
                logger.debug(f"-*- Loaded conversation: {self.id}")
        return self.database_row

    def write_to_storage(self) -> Optional[ConversationRow]:
        """Save the conversation to the storage"""

        if self.storage is not None:
            if self.create_storage:
                self.storage.create()
            self.database_row = self.storage.upsert(conversation=self.to_database_row())
        return self.database_row

    def add_introduction(self, introduction: str) -> None:
        """Add the introduction to the chat history"""

        if introduction is not None:
            if len(self.memory.chat_history) == 0:
                self.memory.add_chat_message(Message(role="assistant", content=introduction))

    def start(self) -> Optional[str]:
        """Start the conversation and return the conversation ID. This function:
        - Creates a new conversation in the storage if it does not exist
        - Load the conversation from the storage if it exists
        """

        # If a database_row exists, return the conversation_id
        if self.database_row is not None:
            return self.database_row.id

        # Create a new conversation or load an existing conversation
        if self.storage is not None:
            # Load existing conversation if it exists
            logger.debug(f"Reading conversation: {self.id}")
            self.read_from_storage()

            # Create a new conversation
            if self.database_row is None:
                logger.debug("-*- Creating new conversation")
                if self.introduction:
                    self.add_introduction(self.introduction)
                self.database_row = self.write_to_storage()
                if self.database_row is None:
                    raise Exception("Failed to create new conversation in storage")
                logger.debug(f"-*- Created conversation: {self.database_row.id}")
                self.from_database_row(row=self.database_row)
                self._api_log_conversation_monitor()
        return self.id

    def end(self) -> None:
        """End the conversation"""
        if self.storage is not None and self.id is not None:
            self.storage.end(conversation_id=self.id)
        self.is_active = False

    def get_json_output_prompt(self) -> str:
        json_output_prompt = "\nProvide your output as a JSON containing the following fields:"
        if self.output_model is not None:
            if isinstance(self.output_model, str):
                json_output_prompt += "\n<json_fields>"
                json_output_prompt += f"\n{self.output_model}"
                json_output_prompt += "\n</json_fields>"
            elif isinstance(self.output_model, list):
                json_output_prompt += "\n<json_fields>"
                json_output_prompt += f"\n{json.dumps(self.output_model)}"
                json_output_prompt += "\n</json_fields>"
            elif issubclass(self.output_model, BaseModel):
                json_schema = self.output_model.model_json_schema()
                if json_schema is not None:
                    output_model_properties = {}
                    json_schema_properties = json_schema.get("properties")
                    if json_schema_properties is not None:
                        for field_name, field_properties in json_schema_properties.items():
                            formatted_field_properties = {
                                prop_name: prop_value
                                for prop_name, prop_value in field_properties.items()
                                if prop_name != "title"
                            }
                            output_model_properties[field_name] = formatted_field_properties

                    if len(output_model_properties) > 0:
                        json_output_prompt += "\n<json_fields>"
                        json_output_prompt += f"\n{json.dumps(list(output_model_properties.keys()))}"
                        json_output_prompt += "\n</json_fields>"
                        json_output_prompt += "\nHere are the properties for each field:"
                        json_output_prompt += "\n<json_field_properties>"
                        json_output_prompt += f"\n{json.dumps(output_model_properties, indent=2)}"
                        json_output_prompt += "\n</json_field_properties>"
            else:
                logger.warning(f"Could not build json schema for {self.output_model}")
        else:
            json_output_prompt += "Provide the output as JSON."

        json_output_prompt += "\nStart your response with `{` and end it with `}`."
        json_output_prompt += "\nYour output will be passed to json.loads() to convert it to a Python object."
        json_output_prompt += "\nMake sure it only contains valid JSON."
        return json_output_prompt

    def get_system_prompt(self) -> Optional[str]:
        """Return the system prompt for the conversation"""

        # If the system_prompt is set, return it
        if self.system_prompt is not None:
            if self.output_model is not None:
                sys_prompt = self.system_prompt
                sys_prompt += f"\n{self.get_json_output_prompt()}"
                return sys_prompt
            return self.system_prompt

        # If the system_prompt_function is set, return the system_prompt from the function
        if self.system_prompt_function is not None:
            system_prompt_kwargs = {"conversation": self}
            _system_prompt_from_function = self.system_prompt_function(**system_prompt_kwargs)
            if _system_prompt_from_function is not None:
                if self.output_model is not None:
                    _system_prompt_from_function += f"\n{self.get_json_output_prompt()}"
                return _system_prompt_from_function
            else:
                raise Exception("system_prompt_function returned None")

        # If use_default_system_prompt is False, return None
        if not self.use_default_system_prompt:
            return None

        # Build a default system prompt
        _system_prompt = "You are a helpful assistant.\n"

        _guidelines = []
        if self.knowledge_base is not None:
            _guidelines.append("Use the information from a knowledge base if it helps respond to the message")
        if self.function_calls:
            _guidelines.append("You have access to tools that you can run to achieve your task.")
            _guidelines.append("Only use the tools you have been provided with")
        if self.markdown and self.output_model is None:
            _guidelines.append("Use markdown to format your answers.")
        if self.output_model is not None:
            _guidelines.append(self.get_json_output_prompt())
        if self.guidelines is not None:
            _guidelines.extend(self.guidelines)

        if len(_guidelines) > 0:
            _system_prompt += "Follow these guidelines:"
            for i, guideline in enumerate(_guidelines, start=1):
                _system_prompt += f"\n{i}. {guideline}"

        # Return the system prompt
        return _system_prompt

    def get_references_from_knowledge_base(self, query: str, num_documents: Optional[int] = None) -> Optional[str]:
        """Return a list of references from the knowledge base"""
        if self.references_function is not None:
            reference_kwargs = {"conversation": self, "query": query}
            return remove_indent(self.references_function(**reference_kwargs))

        if self.knowledge_base is None:
            return None

        relevant_docs: List[Document] = self.knowledge_base.search(query=query, num_documents=num_documents)
        return json.dumps([doc.to_dict() for doc in relevant_docs])

    def get_formatted_chat_history(self) -> Optional[str]:
        """Returns a formatted chat history to use in the user prompt"""

        if self.chat_history_function is not None:
            chat_history_kwargs = {"conversation": self}
            return remove_indent(self.chat_history_function(**chat_history_kwargs))

        formatted_history = self.memory.get_formatted_chat_history(num_messages=self.num_history_messages)
        if formatted_history == "":
            return None
        return remove_indent(formatted_history)

    def get_user_prompt(
        self,
        message: Optional[Union[List[Dict], str]] = None,
        references: Optional[str] = None,
        chat_history: Optional[str] = None,
    ) -> Union[List[Dict], str]:
        """Build the user prompt given a message, references and chat_history"""

        # If the user_prompt is set, return it
        # Note: this ignores the message provided to the run function
        if self.user_prompt is not None:
            return self.user_prompt

        # If the user_prompt_function is set, return the user_prompt from the function
        if self.user_prompt_function is not None:
            user_prompt_kwargs = {
                "conversation": self,
                "message": message,
                "references": references,
                "chat_history": chat_history,
            }
            _user_prompt_from_function = self.user_prompt_function(**user_prompt_kwargs)
            if _user_prompt_from_function is not None:
                return _user_prompt_from_function
            else:
                raise Exception("user_prompt_function returned None")

        if message is None:
            raise Exception("Could not build user prompt. Please provide a user_prompt or an input message.")

        # If use_default_user_prompt is False, return the message as is
        if not self.use_default_user_prompt:
            return message

        # If references and chat_history are None, return the message as is
        if references is None and chat_history is None:
            return message

        # If message is a list, return it as is
        if isinstance(message, list):
            return message

        # Build a default user prompt
        _user_prompt = ""
        # Add references to prompt
        if references:
            _user_prompt += f"""Use the following information from the knowledge base if it helps:
                <knowledge_base>
                {references}
                </knowledge_base>
                \n"""
        # Add chat_history to prompt
        if chat_history:
            _user_prompt += f"""Use the following chat history to reference past messages:
                <chat_history>
                {chat_history}
                </chat_history>
                \n"""
        # Add message to prompt
        _user_prompt += "Respond to the following message"
        if self.user_type:
            _user_prompt += f" from a '{self.user_type}'"
        _user_prompt += ":"
        _user_prompt += f"\nUSER: {message}"
        _user_prompt += "\nASSISTANT: "

        # Return the user prompt
        _user_prompt = cast(str, _user_prompt)
        return _user_prompt

    def get_text_from_message(self, message: Union[List[Dict], str]) -> str:
        """Return the user texts from the message"""
        if isinstance(message, str):
            return message
        if isinstance(message, list):
            text_messages = []
            for m in message:
                m_type = m.get("type")
                if m_type is not None and isinstance(m_type, str):
                    m_value = m.get(m_type)
                    if m_value is not None and isinstance(m_value, str):
                        if m_type == "text":
                            text_messages.append(m_value)
                        # elif m_type == "image_url":
                        #     text_messages.append(f"Image: {m_value}")
                        # else:
                        #     text_messages.append(f"{m_type}: {m_value}")
            if len(text_messages) > 0:
                return "\n".join(text_messages)
        return ""

    def _run(self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True) -> Iterator[str]:
        logger.debug("*********** Conversation Run Start ***********")
        # Load the conversation from the database if available
        self.read_from_storage()

        # -*- Build the system prompt
        system_prompt = self.get_system_prompt()

        # -*- References to add to the user_prompt and send to the api for monitoring
        references: Optional[References] = None

        # -*- Get references to add to the user_prompt
        user_prompt_references = None
        if self.add_references_to_prompt and message and isinstance(message, str):
            reference_timer = Timer()
            reference_timer.start()
            user_prompt_references = self.get_references_from_knowledge_base(query=message)
            reference_timer.stop()
            references = References(
                query=message, references=user_prompt_references, time=round(reference_timer.elapsed, 4)
            )
            logger.debug(f"Time to get references: {reference_timer.elapsed:.4f}s")

        # -*- Get chat history to add to the user prompt
        user_prompt_chat_history = None
        if self.add_chat_history_to_prompt:
            user_prompt_chat_history = self.get_formatted_chat_history()

        # -*- Build the user prompt
        user_prompt: Union[List[Dict], str] = self.get_user_prompt(
            message=message, references=user_prompt_references, chat_history=user_prompt_chat_history
        )

        # -*- Build the messages to send to the LLM
        # Create system message
        system_prompt_message = Message(role="system", content=system_prompt)
        # Create user message
        user_prompt_message = Message(role="user", content=user_prompt)

        # Create message list
        messages: List[Message] = []
        if system_prompt_message.content and system_prompt_message.content != "":
            messages.append(system_prompt_message)
        if self.add_chat_history_to_messages:
            messages += self.memory.get_last_n_messages(last_n=self.num_history_messages)
        messages += [user_prompt_message]

        # -*- Generate response (includes running function calls)
        llm_response = ""
        if stream:
            for response_chunk in self.llm.parsed_response_stream(messages=messages):
                llm_response += response_chunk
                yield response_chunk
        else:
            llm_response = self.llm.parsed_response(messages=messages)

        # -*- Add messages to the memory
        # Add the system prompt to the memory - added only if this is the first message to the LLM
        self.memory.add_system_prompt(message=system_prompt_message)

        # Add user message to the memory - this is added to the chat_history
        self.memory.add_user_message(message=Message(role="user", content=message))

        # Add user prompt to the memory - this is added to the llm_messages
        self.memory.add_llm_message(message=user_prompt_message)

        # Add references to the memory
        if references:
            self.memory.add_references(references=references)

        # Add llm response to the memory - this is added to the chat_history and llm_messages
        self.memory.add_llm_response(message=Message(role="assistant", content=llm_response))

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Send conversation event for monitoring
        event_data = {
            "user_message": message,
            "llm_response": llm_response,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "references": references.model_dump(exclude_none=True) if references else None,
            "metrics": self.llm.metrics,
        }
        self._api_log_conversation_event(event_type="run", event_data=event_data)

        # -*- Update conversation output
        self.output = llm_response

        # -*- Yield final response if not streaming
        if not stream:
            yield llm_response
        logger.debug("*********** Conversation Run End ***********")

    def _run_tasks(self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True) -> Iterator[str]:
        if self.tasks is None or len(self.tasks) == 0:
            return ""

        logger.debug("*********** Conversation Tasks Start ***********")
        # Load the conversation from the database if available
        self.read_from_storage()

        # Add user message to the memory - this is added to the chat_history
        self.memory.add_user_message(message=Message(role="user", content=message))

        # -*- Generate response by running tasks
        # LLM response after running all tasks
        llm_response = ""
        # All messages from the tasks
        task_dicts: List[Dict[str, Any]] = []
        previous_task: Optional[Task] = None
        current_task: Optional[Task] = None
        last_task_response: Optional[str] = None
        for idx, task in enumerate(self.tasks, start=1):
            logger.debug(f"*********** Task: {idx} Start ***********")
            previous_task = current_task
            current_task = task
            current_task_message: Optional[Union[List[Dict], str]] = None
            if previous_task and previous_task.output:
                # Convert current_task_message to json if it is a BaseModel
                if issubclass(previous_task.output.__class__, BaseModel):
                    current_task_message = previous_task.output.model_dump_json(exclude_none=True, indent=2)
                else:
                    current_task_message = previous_task.output
            else:
                current_task_message = message

            # Provide conversation to the task
            current_task.conversation_memory = self.memory
            current_task.conversation_message = message

            # Set Task LLM if not set
            if isinstance(current_task, LLMTask):
                if current_task.llm is None:
                    current_task.llm = self.llm

            # -*- Run Task
            if stream and current_task.streamable:
                for chunk in current_task.run(message=current_task_message, stream=True):
                    llm_response += chunk if isinstance(chunk, str) else ""
                    yield chunk if isinstance(chunk, str) else ""
                yield "\n\n"
                llm_response += "\n\n"
            else:
                task_response = current_task.run(message=current_task_message, stream=False)  # type: ignore
                try:
                    if task_response:
                        if isinstance(task_response, str):
                            last_task_response = task_response
                        elif issubclass(task_response.__class__, BaseModel):
                            last_task_response = task_response.model_dump_json(exclude_none=True, indent=2)
                        else:
                            last_task_response = json.dumps(task_response)

                        if current_task.show_output:
                            if stream:
                                yield last_task_response
                                yield "\n\n"
                            else:
                                llm_response += last_task_response
                                llm_response += "\n\n"
                except Exception as e:
                    logger.debug(f"Failed to convert response to json: {e}")

            # Add task information to the list of tasks
            task_dicts.append(current_task.to_dict())

            # Add task LLM messages to the memory
            if isinstance(current_task, LLMTask):
                self.memory.add_llm_messages(messages=current_task.memory.llm_messages)
                # Add task references to the memory
                for references in current_task.memory.references:
                    self.memory.add_references(references=references)
            logger.debug(f"*********** Task: {idx} End ***********")

        # Add llm response to the memory - this is added to the chat_history
        self.memory.add_chat_message(message=Message(role="assistant", content=llm_response))

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Send conversation event for monitoring
        event_data = {
            "user_message": message,
            "llm_response": llm_response,
            "tasks": task_dicts,
            "metrics": self.llm.metrics,
        }
        self._api_log_conversation_event(event_type="task_run", event_data=event_data)

        # -*- Update conversation output
        self.output = llm_response

        # -*- Yield final response if not streaming
        if not stream:
            yield llm_response
        logger.debug("*********** Conversation Tasks End ***********")

    def run(
        self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True
    ) -> Union[Iterator[str], str, BaseModel]:
        # Run tasks if tasks are set
        if self.tasks and len(self.tasks) > 0:
            resp = self._run_tasks(message=message, stream=stream)
            if stream:
                return resp
            else:
                return next(resp)

        # Run Conversation if tasks are not set
        if self.output_model is not None:
            logger.debug("Stream=False as output_model is set")
            json_resp = next(self._run(message=message, stream=False))
            try:
                structured_llm_output = None
                if (
                    isinstance(self.output_model, str)
                    or isinstance(self.output_model, dict)
                    or isinstance(self.output_model, list)
                ):
                    structured_llm_output = json.loads(json_resp)
                elif issubclass(self.output_model, BaseModel):
                    try:
                        structured_llm_output = self.output_model.model_validate_json(json_resp)
                    except ValidationError:
                        # Check if response starts with ```json
                        if json_resp.startswith("```json"):
                            json_resp = json_resp.replace("```json\n", "").replace("\n```", "")
                            try:
                                structured_llm_output = self.output_model.model_validate_json(json_resp)
                            except ValidationError as exc:
                                logger.warning(f"Failed to validate response: {exc}")

                # -*- Update conversation output to the structured output
                if structured_llm_output is not None:
                    self.output = structured_llm_output
            except Exception as e:
                logger.warning(f"Failed to convert response to output model: {e}")

            return self.output or json_resp
        else:
            resp = self._run(message=message, stream=stream)
            if stream:
                return resp
            else:
                return next(resp)

    def chat(self, message: Union[List[Dict], str], stream: bool = True) -> Union[Iterator[str], str]:
        # Run tasks if tasks are set
        if self.tasks and len(self.tasks) > 0:
            resp = self._run_tasks(message=message, stream=stream)

        # Run Conversation if tasks are not set
        else:
            resp = self._run(message=message, stream=stream)

        if stream:
            return resp
        else:
            return next(resp)

    def _chat_raw(
        self, messages: List[Message], user_message: Optional[str] = None, stream: bool = True
    ) -> Iterator[Dict]:
        logger.debug("*********** Conversation Raw Chat Start ***********")
        # Load the conversation from the database if available
        self.read_from_storage()

        # -*- Add user message to the memory - this is added to the chat_history
        if user_message:
            self.memory.add_user_message(Message(role="user", content=user_message))

        # -*- Add prompts to the memory - these are added to the llm_messages
        self.memory.add_llm_messages(messages=messages)

        # -*- Generate response
        batch_llm_response_message = {}
        if stream:
            for response_delta in self.llm.response_delta(messages=messages):
                yield response_delta
        else:
            batch_llm_response_message = self.llm.response_message(messages=messages)

        # Add llm response to the memory - this is added to the chat_history and llm_messages
        # LLM Response is the last message in the messages list
        llm_response_message = messages[-1]
        try:
            self.memory.add_llm_response(llm_response_message)
        except Exception as e:
            logger.warning(f"Failed to add llm response to memory: {e}")

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Send conversation event for monitoring
        event_data = {
            "user_message": user_message,
            "llm_response": llm_response_message,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "metrics": self.llm.metrics,
        }
        self._api_log_conversation_event(event_type="chat_raw", event_data=event_data)

        # -*- Yield final response if not streaming
        if not stream:
            yield batch_llm_response_message
        logger.debug("*********** Conversation Raw Chat End ***********")

    def chat_raw(
        self, messages: List[Message], user_message: Optional[str] = None, stream: bool = True
    ) -> Union[Iterator[Dict], Dict]:
        if self.tasks and len(self.tasks) > 0:
            raise Exception("chat_raw does not support tasks")
        resp = self._chat_raw(messages=messages, user_message=user_message, stream=stream)
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

        # -*- Log conversation monitor
        self._api_log_conversation_monitor()

    def generate_name(self) -> str:
        """Generate a name for the conversation using chat history"""
        _conv = (
            "Please provide a suitable name for the following conversation in maximum 5 words.\n"
            "Remember, do not exceed 5 words.\n\n"
        )
        for message in self.memory.chat_history[1:6]:
            _conv += f"{message.role.upper()}: {message.content}\n"

        _conv += "\n\nConversation Name:"

        system_message = Message(
            role="system",
            content="Please provide a suitable name for the following conversation in maximum 5 words.",
        )
        user_message = Message(role="user", content=_conv)
        generate_name_messages = [system_message, user_message]
        generated_name = self.llm.parsed_response(messages=generate_name_messages)
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

        # -*- Log conversation monitor
        self._api_log_conversation_monitor()

    ###########################################################################
    # Api functions
    ###########################################################################

    def _api_log_conversation_monitor(self):
        if not self.monitoring:
            return

        from phi.api.conversation import create_conversation_monitor, ConversationMonitorCreate

        try:
            database_row: ConversationRow = self.database_row or self.to_database_row()
            create_conversation_monitor(
                monitor=ConversationMonitorCreate(
                    conversation_id=database_row.id,
                    conversation_data=database_row.conversation_data(),
                ),
            )
        except Exception as e:
            logger.debug(f"Could not create conversation monitor: {e}")

    def _api_log_conversation_event(
        self, event_type: str = "chat", event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        if not self.monitoring:
            return

        from phi.api.conversation import create_conversation_event, ConversationEventCreate

        try:
            database_row: ConversationRow = self.database_row or self.to_database_row()
            create_conversation_event(
                conversation=ConversationEventCreate(
                    conversation_id=database_row.id,
                    conversation_data=database_row.conversation_data(),
                    event_type=event_type,
                    event_data=event_data,
                ),
            )
        except Exception as e:
            logger.debug(f"Could not create conversation event: {e}")

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
        history: List[Dict[str, Any]] = []
        all_chats = self.memory.get_chats()
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
        return self.get_references_from_knowledge_base(query=query)

    ###########################################################################
    # Print Response
    ###########################################################################

    def print_response(
        self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True, markdown: bool = True
    ) -> None:
        from phi.cli.console import console
        from rich.live import Live
        from rich.table import Table
        from rich.status import Status
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from rich.box import ROUNDED
        from rich.markdown import Markdown

        if stream:
            response = ""
            with Live() as live_log:
                status = Status("Working...", spinner="dots")
                live_log.update(status)
                response_timer = Timer()
                response_timer.start()
                for resp in self.run(message, stream=True):
                    response += resp if isinstance(resp, str) else ""
                    _response = response if not markdown else Markdown(response)

                    table = Table(box=ROUNDED, border_style="blue", show_header=False)
                    if message:
                        table.show_header = True
                        table.add_column("Message")
                        table.add_column(self.get_text_from_message(message))
                    table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", _response)  # type: ignore
                    live_log.update(table)
                response_timer.stop()
        else:
            response_timer = Timer()
            response_timer.start()
            with Progress(
                SpinnerColumn(spinner_name="dots"), TextColumn("{task.description}"), transient=True
            ) as progress:
                progress.add_task("Working...")
                response = self.run(message, stream=False)  # type: ignore

            response_timer.stop()
            _response = response if not markdown else Markdown(response)

            table = Table(box=ROUNDED, border_style="blue", show_header=False)
            if message:
                table.show_header = True
                table.add_column("Message")
                table.add_column(self.get_text_from_message(message))
            table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", _response)  # type: ignore
            console.print(table)

    def cli_app(
        self,
        user: str = "User",
        emoji: str = ":sunglasses:",
        stream: bool = True,
        markdown: bool = True,
        exit_on: Tuple[str, ...] = ("exit", "bye"),
    ) -> None:
        from rich.prompt import Prompt

        while True:
            message = Prompt.ask(f"[bold] {emoji} {user} [/bold]")
            if message in exit_on:
                break

            self.print_response(message=message, stream=stream, markdown=markdown)
