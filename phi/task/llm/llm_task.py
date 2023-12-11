import json
from typing import List, Any, Optional, Dict, Iterator, Callable, cast, Union

from pydantic import BaseModel, ValidationError

from phi.document import Document
from phi.knowledge.base import KnowledgeBase
from phi.llm.base import LLM
from phi.llm.openai import OpenAIChat
from phi.llm.message import Message
from phi.llm.references import References
from phi.task.task import Task
from phi.memory.task.llm import LLMTaskMemory
from phi.tools import Tool, ToolRegistry
from phi.utils.format_str import remove_indent
from phi.utils.log import logger
from phi.utils.timer import Timer


class LLMTask(Task):
    # -*- LLM to use for this task
    llm: Optional[LLM] = None

    # -*- Task Memory
    memory: LLMTaskMemory = LLMTaskMemory()
    # Add chat history to the messages sent to the LLM.
    # If True, the chat history is added to the messages sent to the LLM.
    add_chat_history_to_messages: bool = False
    # Number of previous messages to add to prompt or messages sent to the LLM.
    num_history_messages: int = 8

    # -*- Task Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None
    # Add references from the knowledge base to the prompt sent to the LLM.
    add_references_to_prompt: bool = False

    # -*- Enable Function Calls
    # Makes the task Autonomous by letting the LLM call functions to achieve tasks.
    function_calls: bool = False
    # Add default functions to the LLM when function_calls is True.
    default_functions: bool = True
    # Show function calls in LLM messages.
    show_function_calls: bool = False
    # Maximum number of function calls allowed.
    function_call_limit: Optional[int] = None

    # -*- Task Tools
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

    #
    # -*- Prompt Settings
    #
    # -*- System prompt: provide the system prompt as a string
    system_prompt: Optional[str] = None
    # -*- System prompt function: provide the system prompt as a function
    # This function is provided the task as an argument
    #   and should return the system_prompt as a string.
    # Signature:
    # def system_prompt_function(task: Task) -> str:
    #    ...
    system_prompt_function: Optional[Callable[..., Optional[str]]] = None
    # If True, the task provides a default system prompt
    use_default_system_prompt: bool = True

    # -*- User prompt: provide the user prompt as a string
    # Note: this will ignore the message provided to the run function
    user_prompt: Optional[Union[List[Dict], str]] = None
    # -*- User prompt function: provide the user prompt as a function.
    # This function is provided the task and the input message as arguments
    #   and should return the user_prompt as a Union[List[Dict], str].
    # If add_references_to_prompt is True, then references are also provided as an argument.
    # Signature:
    # def custom_user_prompt_function(
    #     task: Task,
    #     message: Optional[Union[List[Dict], str]] = None,
    #     references: Optional[str] = None,
    # ) -> str:
    #     ...
    user_prompt_function: Optional[Callable[..., str]] = None
    # If True, the task provides a default user prompt
    use_default_user_prompt: bool = True
    # Function to build references for the default user_prompt
    # This function, if provided, is called when add_references_to_prompt is True
    # Signature:
    # def references(task: Task, query: str) -> Optional[str]:
    #     ...
    references_function: Optional[Callable[..., Optional[str]]] = None

    # -*- Output Settings
    # Format the output using markdown
    markdown: bool = True
    # List of guidelines for the default system prompt
    guidelines: Optional[List[str]] = None

    def add_tools_to_llm(self) -> None:
        if self.llm is None:
            return

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

    def get_default_llm(self) -> LLM:
        default_llm = OpenAIChat()
        if self.output_model is not None:
            default_llm.response_format = {"type": "json_object"}
        return default_llm

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
        """Return the system prompt for the task"""

        # If the system_prompt is set, return it
        if self.system_prompt is not None:
            if self.output_model is not None:
                sys_prompt = self.system_prompt
                sys_prompt += f"\n{self.get_json_output_prompt()}"
                return sys_prompt
            return self.system_prompt

        # If the system_prompt_function is set, return the system_prompt from the function
        if self.system_prompt_function is not None:
            system_prompt_kwargs = {"task": self}
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
        _system_prompt = cast(str, _system_prompt)
        return _system_prompt

    def get_references_from_knowledge_base(self, query: str, num_documents: Optional[int] = None) -> Optional[str]:
        """Return a list of references from the knowledge base"""
        if self.references_function is not None:
            reference_kwargs = {"task": self, "query": query}
            return remove_indent(self.references_function(**reference_kwargs))

        if self.knowledge_base is None:
            return None

        relevant_docs: List[Document] = self.knowledge_base.search(query=query, num_documents=num_documents)
        return json.dumps([doc.to_dict() for doc in relevant_docs])

    def get_user_prompt(
        self, message: Optional[Union[List[Dict], str]] = None, references: Optional[str] = None
    ) -> Union[List[Dict], str]:
        """Build the user prompt given a message and references"""

        # If the user_prompt is set, return it
        # Note: this ignores the message provided to the run function
        if self.user_prompt is not None:
            return self.user_prompt

        # If the user_prompt_function is set, return the user_prompt from the function
        if self.user_prompt_function is not None:
            user_prompt_kwargs = {
                "task": self,
                "message": message,
                "references": references,
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
        if references is None:
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
        # Add message to prompt
        _user_prompt += "Respond to the following message:"
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
                        # if m_type == "image_url":
                        #     text_messages.append(f"Image: {m_value}")
                        # else:
                        #     text_messages.append(f"{m_type}: {m_value}")
            if len(text_messages) > 0:
                return "\n".join(text_messages)
        return ""

    def prepare_task(self) -> None:
        super().prepare_task()
        self.add_tools_to_llm()

    def _run(
        self,
        message: Optional[Union[List[Dict], str]] = None,
        stream: bool = True,
    ) -> Iterator[str]:
        # -*- Set default LLM
        if self.llm is None:
            self.llm = self.get_default_llm()

        # -*- Prepare the task
        self.prepare_task()

        # -*- Build the system prompt
        system_prompt = self.get_system_prompt()

        # -*- References to add to the user_prompt and save to the task memory
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

        # -*- Build the user prompt
        user_prompt: Union[List[Dict], str] = self.get_user_prompt(message=message, references=user_prompt_references)

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

        # -*- Update task output
        self.output = llm_response

        # -*- Yield final response if not streaming
        if not stream:
            yield llm_response

    def run(
        self,
        message: Optional[Union[List[Dict], str]] = None,
        stream: bool = True,
    ) -> Union[Iterator[str], str, BaseModel]:
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

    def to_dict(self) -> Dict[str, Any]:
        _dict = {
            "id": self.id,
            "name": self.name,
            "meta_data": self.meta_data,
            "output": self.output,
            "chat_history": self.memory.get_chat_history(),
            "llm_messages": self.memory.get_llm_messages(),
            "references": self.memory.references,
            "llm": self.llm.to_dict() if self.llm else None,
            "metrics": self.llm.metrics if self.llm else None,
        }
        return _dict

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
