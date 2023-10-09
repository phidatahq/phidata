import json
from uuid import uuid4
from typing import List, Any, Optional, Dict, Iterator, Callable, cast, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field

from phi.document import Document
from phi.knowledge.base import KnowledgeBase
from phi.llm.base import LLM
from phi.llm.openai import OpenAIChat
from phi.llm.schemas import Message
from phi.llm.function.registry import FunctionRegistry
from phi.utils.format_str import remove_indent
from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.timer import Timer


class Task(BaseModel):
    # -*- LLM to use for this task
    llm: LLM = OpenAIChat()

    # -*- Task settings
    # Task UUID
    id: Optional[str] = Field(None, validate_default=True)
    # Task name
    name: Optional[str] = None
    # Metadata associated with this task
    meta_data: Optional[Dict[str, Any]] = None

    # -*- Task Output
    output: Optional[Any] = None

    # -*- Task Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None
    # Add references from the knowledge base to the prompt sent to the LLM.
    add_references_to_prompt: bool = False

    # -*- Enable Function Calls
    # Makes the task autonomous.
    function_calls: bool = False
    # Add a list of default functions to the LLM
    default_functions: bool = True
    # Show function calls in LLM messages.
    show_function_calls: bool = False
    # A list of functions to add to the LLM.
    functions: Optional[List[Callable]] = None
    # A list of function registries to add to the LLM.
    function_registries: Optional[List[FunctionRegistry]] = None

    #
    # -*- Prompt Settings
    #
    # -*- System prompt: provide the system prompt as a string or using a function
    system_prompt: Optional[str] = None
    # Function to build the system prompt.
    # This function is provided the task as an argument
    #   and should return the system_prompt as a string.
    # Signature:
    # def system_prompt_function(task: Task) -> str:
    #    ...
    system_prompt_function: Optional[Callable[..., Optional[str]]] = None
    # If True, the task provides a default system prompt
    use_default_system_prompt: bool = True

    # -*- User prompt: provide the user prompt as a string or using a function
    # Note: this will ignore the input provided to the run function
    user_prompt: Optional[str] = None
    # Function to build the user prompt.
    # This function is provided the task and the input as arguments
    #   and should return the user_prompt as a string.
    # If add_references_to_prompt is True, then references are also provided as an argument.
    # Signature:
    # def custom_user_prompt_function(
    #     task: Task,
    #     message: Optional[str] = None,
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

    # If True, show debug logs
    debug_mode: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("id", mode="before")
    def set_task_id(cls, v: Optional[str]) -> str:
        return v if v is not None else str(uuid4())

    @field_validator("debug_mode", mode="before")
    def set_log_level(cls, v: bool) -> bool:
        if v:
            set_log_level_to_debug()
            logger.debug("Debug logs enabled")
        return v

    @model_validator(mode="after")
    def add_functions_to_llm(self) -> "Task":
        if self.function_calls:
            if self.default_functions:
                default_func_list: List[Callable] = [self.search_knowledge_base]
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
        return self

    def get_references_from_knowledge_base(self, query: str, num_documents: Optional[int] = None) -> Optional[str]:
        """Return a list of references from the knowledge base"""

        if self.references_function is not None:
            reference_kwargs = {"task": self, "query": query}
            return remove_indent(self.references_function(**reference_kwargs))

        if self.knowledge_base is None:
            return None

        relevant_docs: List[Document] = self.knowledge_base.search(query=query, num_documents=num_documents)
        return json.dumps([doc.to_dict() for doc in relevant_docs])

    def get_system_prompt(self) -> Optional[str]:
        """Return the system prompt for the task"""

        # If the system_prompt is set, return it
        if self.system_prompt is not None:
            return "\n".join([line.strip() for line in self.system_prompt.split("\n")])

        # If the system_prompt_function is set, return the system_prompt from the function
        if self.system_prompt_function is not None:
            system_prompt_kwargs = {"task": self}
            _system_prompt_from_function = remove_indent(self.system_prompt_function(**system_prompt_kwargs))
            if _system_prompt_from_function is not None:
                return _system_prompt_from_function
            else:
                raise Exception("system_prompt_function returned None")

        # If use_default_system_prompt is False, return None
        if not self.use_default_system_prompt:
            return None

        # Build a default system prompt
        _system_prompt = "You are a helpful assistant.\n"

        if self.knowledge_base is not None:
            _system_prompt += "You have access to a knowledge base that you can search for information.\n"

        if self.function_calls:
            _system_prompt += "You have access to functions that you can run to help you respond to the user.\n"

        # Return the system prompt after removing newlines and indenting
        _system_prompt = cast(str, remove_indent(_system_prompt))
        return _system_prompt

    def get_user_prompt(self, message: Optional[str] = None, references: Optional[str] = None) -> str:
        """Build the user prompt given a message and references"""

        # If the user_prompt is set, return it
        # Note: this ignores the message provided to the run function
        if self.user_prompt is not None:
            return "\n".join([line.strip() for line in self.user_prompt.split("\n")])

        # If the user_prompt_function is set, return the user_prompt from the function
        if self.user_prompt_function is not None:
            user_prompt_kwargs = {
                "task": self,
                "message": message,
                "references": references,
            }
            _user_prompt_from_function = remove_indent(self.user_prompt_function(**user_prompt_kwargs))
            if _user_prompt_from_function is not None:
                return _user_prompt_from_function
            else:
                raise Exception("user_prompt_function returned None")

        if message is None:
            raise Exception("Could not build user prompt. Please provide an input message.")

        # If use_default_user_prompt is False, return the message as is
        if not self.use_default_user_prompt:
            return message

        # If references and chat_history are None, return the message as is
        if references is None:
            return message

        # Build a default user prompt
        _user_prompt = "Respond to the following message in the best way possible.\n"

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

        # Remind the LLM of its task
        # if references:
        #     _user_prompt += "\nRemember, your task is to respond to the following message."

        _user_prompt += f"\nUSER: {message}"
        _user_prompt += "\nASSISTANT: "

        # Return the user prompt after removing newlines and indenting
        _user_prompt = cast(str, remove_indent(_user_prompt))
        return _user_prompt

    def _run(self, message: Optional[str] = None, stream: bool = True) -> Iterator[str]:
        logger.debug("*********** Task Run Start ***********")

        # -*- Build the system prompt
        system_prompt = self.get_system_prompt()

        # -*- Get references to add to the user_prompt
        user_prompt_references = None
        if self.add_references_to_prompt and message:
            reference_timer = Timer()
            reference_timer.start()
            user_prompt_references = self.get_references_from_knowledge_base(query=message)
            reference_timer.stop()
            logger.debug(f"Time to get references: {reference_timer.elapsed:.4f}s")

        # -*- Build the user prompt
        user_prompt = self.get_user_prompt(message=message, references=user_prompt_references)

        # -*- Build the messages to send to the LLM
        # Create system message
        system_prompt_message = Message(role="system", content=system_prompt)
        # Create user message
        user_prompt_message = Message(role="user", content=user_prompt)

        # Create message list
        messages: List[Message] = []
        if system_prompt_message.content and system_prompt_message.content != "":
            messages.append(system_prompt_message)
        messages += [user_prompt_message]

        # -*- Generate response (includes running function calls)
        llm_response = ""
        if stream:
            for response_chunk in self.llm.parsed_response_stream(messages=messages):
                llm_response += response_chunk
                yield response_chunk
        else:
            llm_response = self.llm.parsed_response(messages=messages)

        # -*- Yield final response if not streaming
        if not stream:
            yield llm_response
        logger.debug("*********** Task Run End ***********")

    def run(self, message: Optional[str] = None, stream: bool = True) -> Union[Iterator[str], str]:
        resp = self._run(message=message, stream=stream)
        if stream:
            return resp
        else:
            return next(resp)

    ###########################################################################
    # LLM functions
    ###########################################################################

    def search_knowledge_base(self, query: str) -> Optional[str]:
        """Search the knowledge base for information about a users query.

        :param query: The query to search for.
        :return: A string containing the response from the knowledge base.
        """
        return self.get_references_from_knowledge_base(query=query)

    ###########################################################################
    # Print Response
    ###########################################################################

    def print_response(self, message: str, stream: bool = True) -> None:
        from phi.cli.console import console
        from rich.live import Live
        from rich.table import Table
        from rich.box import ROUNDED
        from rich.markdown import Markdown

        if stream:
            response = ""
            with Live() as live_log:
                response_timer = Timer()
                response_timer.start()
                for resp in self.run(message, stream=True):
                    response += resp

                    table = Table(box=ROUNDED, border_style="blue")
                    table.add_column("Message")
                    table.add_column(message)
                    md_response = Markdown(response)
                    table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", md_response)
                    live_log.update(table)
                response_timer.stop()
        else:
            response_timer = Timer()
            response_timer.start()
            response = self.run(message, stream=False)  # type: ignore
            response_timer.stop()
            md_response = Markdown(response)
            table = Table(box=ROUNDED, border_style="blue")
            table.add_column("Message")
            table.add_column(message)
            table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", md_response)
            console.print(table)
