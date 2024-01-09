import json
from uuid import uuid4
from datetime import datetime
from collections import OrderedDict
from typing import List, Any, Optional, Dict, Iterator, Callable, Union, Type, Tuple

from pydantic import BaseModel, ConfigDict, field_validator, Field, ValidationError

from phi.assistant import Assistant
from phi.conversation.row import ConversationRow
from phi.knowledge.base import KnowledgeBase
from phi.llm.base import LLM
from phi.llm.openai import OpenAIChat
from phi.llm.message import Message
from phi.llm.references import References  # noqa: F401
from phi.memory.conversation import ConversationMemory
from phi.storage.conversation import ConversationStorage
from phi.task.task import Task
from phi.task.llm import LLMTask
from phi.tools import Tool, ToolRegistry, Function
from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.message import get_text_from_message
from phi.utils.merge_dict import merge_dictionaries
from phi.utils.timer import Timer


class Conversation(BaseModel):
    # -*- LLM settings
    # The LLM used for this conversation
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
    # Extra data associated with this conversation
    extra_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this conversation was created in the database
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated in the database
    updated_at: Optional[datetime] = None

    # -*- Conversation Memory
    memory: ConversationMemory = ConversationMemory()
    # Add chat history to the messages sent to the LLM.
    # If True, the chat history is added to the messages sent to the LLM.
    add_chat_history_to_messages: bool = False
    # Add chat history to the prompt sent to the LLM.
    # If True, a formatted chat history is added to the default user_prompt.
    add_chat_history_to_prompt: bool = False
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
    tools: Optional[List[Union[Tool, ToolRegistry, Callable, Dict, Function]]] = None
    # Controls which (if any) function is called by the model.
    # "none" means the model will not call a function and instead generates a message.
    # "auto" means the model can pick between generating a message or calling a function.
    # Specifying a particular function via {"type: "function", "function": {"name": "my_function"}}
    #   forces the model to call that function.
    # "none" is the default when no functions are present. "auto" is the default if functions are present.
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None

    # -*- Conversation Assistants
    assistants: Optional[List[Assistant]] = None
    show_assistant_responses: bool = False

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
    # List of guidelines to add to the default system prompt
    guidelines: Optional[List[str]] = None
    # -*- Last LLM response i.e. the final output of this conversation
    output: Optional[Any] = None

    # -*- Tasks
    # Generate a response using tasks instead of a prompt
    # If tasks is None or empty, a default LLM task is created for this conversation
    tasks: Optional[List[Task]] = None
    # Metadata about the conversation tasks
    _meta_data: Optional[Dict[str, Any]] = None

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

    @property
    def streamable(self) -> bool:
        return self.output_model is None

    @property
    def llm_task(self) -> LLMTask:
        """Returns an LLMTask for this conversation"""

        _llm_task = LLMTask(
            llm=self.llm.model_copy(),
            conversation_memory=self.memory,
            add_references_to_prompt=self.add_references_to_prompt,
            add_chat_history_to_messages=self.add_chat_history_to_messages,
            num_history_messages=self.num_history_messages,
            knowledge_base=self.knowledge_base,
            function_calls=self.function_calls,
            default_functions=self.default_functions,
            show_function_calls=self.show_function_calls,
            function_call_limit=self.function_call_limit,
            tools=self.tools,
            tool_choice=self.tool_choice,
            system_prompt=self.system_prompt,
            system_prompt_function=self.system_prompt_function,
            use_default_system_prompt=self.use_default_system_prompt,
            user_prompt=self.user_prompt,
            user_prompt_function=self.user_prompt_function,
            use_default_user_prompt=self.use_default_user_prompt,
            references_function=self.references_function,
            chat_history_function=self.chat_history_function,
            output_model=self.output_model,
            markdown=self.markdown,
            guidelines=self.guidelines,
        )
        return _llm_task

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
            meta_data=self._meta_data,
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
                logger.debug(f"Loaded conversation memory: {self.memory.llm_messages}")
            except Exception as e:
                logger.warning(f"Failed to load conversation memory: {e}")

        # Update meta_data from the database if available
        if row.meta_data is not None:
            self._meta_data = row.meta_data

        # Update extra_data from the database
        if row.extra_data is not None:
            # If extra_data is set in the conversation, merge it with the database extra_data.
            # The conversation extra_data takes precedence
            if self.extra_data is not None and row.extra_data is not None:
                # Updates row.extra_data with self.extra_data
                merge_dictionaries(row.extra_data, self.extra_data)
                self.extra_data = row.extra_data
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

        # If a database_row exists, return the id from the database_row
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

    def get_delegation_functions_for_task(
        self, task: Task, assistant_responses: Optional[Dict[str, List[str]]] = None
    ) -> Optional[List[Function]]:
        if self.assistants is None or len(self.assistants) == 0:
            return None

        delegation_functions: List[Function] = []
        for assistant in self.assistants:
            delegation_functions.append(
                assistant.get_delegation_function(task=task, assistant_responses=assistant_responses)
            )
        return delegation_functions

    def _run(self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True) -> Iterator[str]:
        logger.debug(f"*********** Conversation Start: {self.id} ***********")
        # Load the conversation from the database if available
        self.read_from_storage()

        # Add a default LLM Task if tasks are empty
        _tasks = self.tasks
        if _tasks is None or len(_tasks) == 0:
            _tasks = [self.llm_task]

        # meta_data for all tasks in this run
        conversation_tasks: List[Dict[str, Any]] = []
        # Final LLM response after running all tasks
        conversation_run_response = ""
        assistant_responses: Dict[str, List[str]] = OrderedDict()

        # Messages for this run
        # TODO: remove this when frontend is updated
        run_messages: List[Message] = []

        # -*- Generate response by running tasks
        current_task: Optional[Task] = None
        for idx, task in enumerate(_tasks, start=1):
            logger.debug(f"*********** Task: {idx} Start ***********")

            # Set previous_task and current_task
            previous_task = current_task
            current_task = task

            # -*- Prepare input message for the current_task
            current_task_message: Optional[Union[List[Dict], str]] = None
            if previous_task and previous_task.output is not None:
                # Convert current_task_message to json if it is a BaseModel
                if issubclass(previous_task.output.__class__, BaseModel):
                    current_task_message = previous_task.output.model_dump_json(exclude_none=True, indent=2)
                else:
                    current_task_message = previous_task.output
            else:
                current_task_message = message

            # -*- Update Task
            # Add conversation state to the task
            current_task.conversation_id = self.id
            current_task.conversation_memory = self.memory
            current_task.conversation_message = message
            current_task.conversation_tasks = conversation_tasks
            # Set output parsing off
            current_task.parse_output = False

            # -*- Update LLMTask
            if isinstance(current_task, LLMTask):
                # Update LLM
                if current_task.llm is None:
                    current_task.llm = self.llm.model_copy()

                # Add delegation functions to the task
                delegation_functions = self.get_delegation_functions_for_task(
                    task=current_task, assistant_responses=assistant_responses
                )
                if delegation_functions and len(delegation_functions) > 0:
                    if current_task.tools is None:
                        current_task.tools = []
                    current_task.tools.extend(delegation_functions)

            # -*- Run Task
            if stream and current_task.streamable:
                for chunk in current_task.run(message=current_task_message, stream=True):
                    if current_task.show_output:
                        conversation_run_response += chunk if isinstance(chunk, str) else ""
                        yield chunk if isinstance(chunk, str) else ""
                if current_task.show_output:
                    yield "\n\n"
                    conversation_run_response += "\n\n"
            else:
                current_task_response = current_task.run(message=current_task_message, stream=False)  # type: ignore
                current_task_response_str = ""
                try:
                    if current_task_response:
                        if isinstance(current_task_response, str):
                            current_task_response_str = current_task_response
                        elif issubclass(current_task_response.__class__, BaseModel):
                            current_task_response_str = current_task_response.model_dump_json(
                                exclude_none=True, indent=2
                            )
                        else:
                            current_task_response_str = json.dumps(current_task_response)

                        if current_task.show_output:
                            if stream:
                                yield current_task_response_str
                                yield "\n\n"
                            else:
                                conversation_run_response += current_task_response_str
                                conversation_run_response += "\n\n"
                except Exception as e:
                    logger.debug(f"Failed to convert response to json: {e}")

            # TODO: remove this when frontend is updated
            if isinstance(current_task, LLMTask):
                run_messages.extend(current_task.memory.llm_messages)

        # -*- Show assistant responses
        if self.show_assistant_responses and len(assistant_responses) > 0:
            assistant_responses_str = ""
            for assistant_name, assistant_response_list in assistant_responses.items():
                assistant_responses_str += f"{assistant_name}:\n"
                for assistant_response in assistant_response_list:
                    assistant_responses_str += f"\n{assistant_response}\n"
            if stream:
                yield assistant_responses_str
            else:
                conversation_run_response += assistant_responses_str

        # -*- Save conversation to storage
        self.write_to_storage()

        # -*- Send conversation event for monitoring
        event_info = {
            "tasks": conversation_tasks,
            "messages": [m.model_dump(exclude_none=True) for m in run_messages if m is not None],
        }
        event_data = {
            "user_message": message,
            "llm_response": conversation_run_response,
            "info": event_info,
            "metrics": self.llm.metrics,
        }
        self._api_log_conversation_event(event_type="run", event_data=event_data)

        # -*- Update conversation output
        self.output = conversation_run_response

        # -*- Yield final response if not streaming
        if not stream:
            yield conversation_run_response
        logger.debug(f"*********** Conversation End: {self.id} ***********")

    def run(
        self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True
    ) -> Union[Iterator[str], str, BaseModel]:
        # Convert response into structured output if output_model is set
        if self.output_model is not None:
            logger.debug("Setting stream=False as output_model is set")
            json_resp = next(self._run(message=message, stream=False))
            try:
                structured_output = None
                if (
                    isinstance(self.output_model, str)
                    or isinstance(self.output_model, dict)
                    or isinstance(self.output_model, list)
                ):
                    structured_output = json.loads(json_resp)
                elif issubclass(self.output_model, BaseModel):
                    try:
                        structured_output = self.output_model.model_validate_json(json_resp)
                    except ValidationError:
                        # Check if response starts with ```json
                        if json_resp.startswith("```json"):
                            json_resp = json_resp.replace("```json\n", "").replace("\n```", "")
                            try:
                                structured_output = self.output_model.model_validate_json(json_resp)
                            except ValidationError as exc:
                                logger.warning(f"Failed to validate response: {exc}")

                # -*- Update conversation output to the structured output
                if structured_output is not None:
                    self.output = structured_output
            except Exception as e:
                logger.warning(f"Failed to convert response to output model: {e}")

            return self.output or json_resp
        else:
            if stream and self.streamable:
                resp = self._run(message=message, stream=True)
                return resp
            else:
                resp = self._run(message=message, stream=False)
                return next(resp)

    def chat(self, message: Union[List[Dict], str], stream: bool = True) -> Union[Iterator[str], str, BaseModel]:
        return self.run(message=message, stream=stream)

    def _chat_raw(
        self, messages: List[Message], user_message: Optional[str] = None, stream: bool = True
    ) -> Iterator[Dict]:
        logger.debug("*********** Conversation Raw Chat Start ***********")
        # Load the conversation from the database if available
        self.read_from_storage()

        # -*- Add user message to the memory - this is added to the chat_history
        if user_message:
            self.memory.add_chat_message(Message(role="user", content=user_message))

        # -*- Generate response
        batch_llm_response_message = {}
        if stream:
            for response_delta in self.llm.response_delta(messages=messages):
                yield response_delta
        else:
            batch_llm_response_message = self.llm.response_message(messages=messages)

        # -*- Add prompts and response to the memory - these are added to the llm_messages
        self.memory.add_llm_messages(messages=messages)

        # Add llm response to the chat history
        # LLM Response is the last message in the messages list
        llm_response_message = messages[-1]
        try:
            self.memory.add_chat_message(llm_response_message)
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

        if self.output_model is not None:
            markdown = False
            stream = False

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
                        table.add_column(get_text_from_message(message))
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
                table.add_column(get_text_from_message(message))
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
