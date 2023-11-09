from uuid import uuid4
from typing import List, Any, Optional, Dict, Iterator, Callable, cast, Union

from pydantic import BaseModel, ConfigDict, Field

from phi.document import Document
from phi.knowledge.base import KnowledgeBase
from phi.llm.base import LLM
from phi.llm.schemas import Message, References
from phi.llm.openai import OpenAIChat
from phi.llm.agent.base import BaseAgent
from phi.llm.function.registry import FunctionRegistry
from phi.llm.task.memory.base import TaskMemory
from phi.utils.format_str import remove_indent
from phi.utils.log import logger
from phi.utils.timer import Timer


class LLMTask(BaseModel):
    # -*- LLM to use for this task
    llm: Optional[LLM] = None

    # -*- Task settings
    # Task UUID
    id: Optional[str] = Field(None, validate_default=True)
    # Task name
    name: Optional[str] = None
    # Metadata associated with this task
    meta_data: Optional[Dict[str, Any]] = None

    # -*- Task Memory
    memory: TaskMemory = TaskMemory()
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

    # -*- Agents
    # Add a list of agents to the LLM
    # function_calls must be True for agents to be added to the LLM
    agents: Optional[List[BaseAgent]] = None

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
    # Note: this will ignore the message provided to the run function
    user_prompt: Optional[Union[List[Dict], str]] = None
    # Function to build the user prompt.
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

    # -*- Task Output
    output: Optional[Any] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def set_task_id(self) -> None:
        if self.id is None:
            self.id = str(uuid4())

    def add_functions_to_llm(self) -> None:
        if self.llm is None:
            return

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

    def add_agents_to_llm(self) -> None:
        if self.llm is None:
            return

        if self.agents is not None and len(self.agents) > 0:
            for agent in self.agents:
                self.llm.add_agent(agent)

            # Set function call to auto if it is not set
            if self.llm.function_call is None:
                self.llm.function_call = "auto"

            # Set show_function_calls if it is not set on the llm
            if self.llm.show_function_calls is None:
                self.llm.show_function_calls = self.show_function_calls

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

    def get_references_from_knowledge_base(self, query: str, num_documents: Optional[int] = None) -> Optional[str]:
        """Return a list of references from the knowledge base"""
        import json

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
            raise Exception("Could not build user prompt. Please provide an input message.")

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

        _user_prompt += f"\nUSER: {message}"
        _user_prompt += "\nASSISTANT: "

        # Return the user prompt after removing newlines and indenting
        _user_prompt = cast(str, remove_indent(_user_prompt))
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

    def _run(self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True) -> Iterator[str]:
        # -*- Set default LLM
        if self.llm is None:
            self.llm = OpenAIChat()

        # -*- Prepare the task
        self.set_task_id()
        self.add_functions_to_llm()
        self.add_agents_to_llm()

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

    def run(self, message: Optional[Union[List[Dict], str]] = None, stream: bool = True) -> Union[Iterator[str], str]:
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
        import json

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

    def print_response(self, message: Union[List[Dict], str], stream: bool = True) -> None:
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
                    table.add_column(self.get_text_from_message(message))
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
            table.add_column(self.get_text_from_message(message))
            table.add_row(f"Response\n({response_timer.elapsed:.1f}s)", md_response)
            console.print(table)
