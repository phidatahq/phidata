from typing import List, Iterator, Optional, Dict, Any, Callable, Union

from pydantic import BaseModel, ConfigDict

from phi.llm.message import Message
from phi.tools import Tool, Toolkit
from phi.tools.function import Function, FunctionCall
from phi.utils.timer import Timer
from phi.utils.log import logger


class LLM(BaseModel):
    # ID of the model to use.
    model: str
    # Name for this LLM. Note: This is not sent to the LLM API.
    name: Optional[str] = None
    # Metrics collected for this LLM. Note: This is not sent to the LLM API.
    metrics: Dict[str, Any] = {}
    response_format: Optional[Any] = None

    # A list of tools provided to the LLM.
    # Tools are functions the model may generate JSON inputs for.
    # If you provide a dict, it is not called by the model.
    # Always add tools using the add_tool() method.
    tools: Optional[List[Union[Tool, Dict]]] = None
    # Controls which (if any) function is called by the model.
    # "none" means the model will not call a function and instead generates a message.
    # "auto" means the model can pick between generating a message or calling a function.
    # Specifying a particular function via {"type: "function", "function": {"name": "my_function"}}
    #   forces the model to call that function.
    # "none" is the default when no functions are present. "auto" is the default if functions are present.
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    # If True, runs the tool before sending back the response content.
    run_tools: bool = True
    # If True, shows function calls in the response.
    show_tool_calls: Optional[bool] = None

    # -*- Functions available to the LLM to call -*-
    # Functions extracted from the tools.
    # Note: These are not sent to the LLM API and are only used for execution + deduplication.
    functions: Optional[Dict[str, Function]] = None
    # Maximum number of function calls allowed across all iterations.
    function_call_limit: int = 10
    # Function call stack.
    function_call_stack: Optional[List[FunctionCall]] = None

    system_prompt: Optional[str] = None
    instructions: Optional[List[str]] = None

    # State from the run
    run_id: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        raise NotImplementedError

    def invoke(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    async def ainvoke(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def invoke_stream(self, *args, **kwargs) -> Iterator[Any]:
        raise NotImplementedError

    async def ainvoke_stream(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def response(self, messages: List[Message]) -> str:
        raise NotImplementedError

    async def aresponse(self, messages: List[Message]) -> str:
        raise NotImplementedError

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        raise NotImplementedError

    async def aresponse_stream(self, messages: List[Message]) -> Any:
        raise NotImplementedError

    def generate(self, messages: List[Message]) -> Dict:
        raise NotImplementedError

    def generate_stream(self, messages: List[Message]) -> Iterator[Dict]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(include={"name", "model", "metrics"})
        if self.functions:
            _dict["functions"] = {k: v.to_dict() for k, v in self.functions.items()}
            _dict["function_call_limit"] = self.function_call_limit
        return _dict

    def get_tools_for_api(self) -> Optional[List[Dict[str, Any]]]:
        if self.tools is None:
            return None

        tools_for_api = []
        for tool in self.tools:
            if isinstance(tool, Tool):
                tools_for_api.append(tool.to_dict())
            elif isinstance(tool, Dict):
                tools_for_api.append(tool)
        return tools_for_api

    def add_tool(self, tool: Union[Tool, Toolkit, Callable, Dict, Function]) -> None:
        if self.tools is None:
            self.tools = []

        # If the tool is a Tool or Dict, add it directly to the LLM
        if isinstance(tool, Tool) or isinstance(tool, Dict):
            if tool not in self.tools:
                self.tools.append(tool)
                logger.debug(f"Added tool {tool} to LLM.")

        # If the tool is a Callable or Toolkit, add its functions to the LLM
        elif callable(tool) or isinstance(tool, Toolkit) or isinstance(tool, Function):
            if self.functions is None:
                self.functions = {}

            if isinstance(tool, Toolkit):
                # For each function in the toolkit
                for name, func in tool.functions.items():
                    # If the function does not exist in self.functions, add to self.tools
                    if name not in self.functions:
                        self.functions[name] = func
                        self.tools.append({"type": "function", "function": func.to_dict()})
                        logger.debug(f"Function {name} from {tool.name} added to LLM.")

            elif isinstance(tool, Function):
                if tool.name not in self.functions:
                    self.functions[tool.name] = tool
                    self.tools.append({"type": "function", "function": tool.to_dict()})
                    logger.debug(f"Function {tool.name} added to LLM.")

            elif callable(tool):
                try:
                    function_name = tool.__name__
                    if function_name not in self.functions:
                        func = Function.from_callable(tool)
                        self.functions[func.name] = func
                        self.tools.append({"type": "function", "function": func.to_dict()})
                        logger.debug(f"Function {func.name} added to LLM.")
                except Exception as e:
                    logger.warning(f"Could not add function {tool}: {e}")

    def deactivate_function_calls(self) -> None:
        # Deactivate tool calls by setting future tool calls to "none"
        # This is triggered when the function call limit is reached.
        self.tool_choice = "none"

    def run_function_calls(self, function_calls: List[FunctionCall], role: str = "tool") -> List[Message]:
        function_call_results: List[Message] = []
        for function_call in function_calls:
            if self.function_call_stack is None:
                self.function_call_stack = []

            # -*- Run function call
            _function_call_timer = Timer()
            _function_call_timer.start()
            function_call_success = function_call.execute()
            _function_call_timer.stop()

            _function_call_result = Message(
                role=role,
                content=function_call.result if function_call_success else function_call.error,
                tool_call_id=function_call.call_id,
                tool_call_name=function_call.function.name,
                tool_call_error=not function_call_success,
                metrics={"time": _function_call_timer.elapsed},
            )
            if "tool_call_times" not in self.metrics:
                self.metrics["tool_call_times"] = {}
            if function_call.function.name not in self.metrics["tool_call_times"]:
                self.metrics["tool_call_times"][function_call.function.name] = []
            self.metrics["tool_call_times"][function_call.function.name].append(_function_call_timer.elapsed)
            function_call_results.append(_function_call_result)
            self.function_call_stack.append(function_call)

            # -*- Check function call limit
            if len(self.function_call_stack) >= self.function_call_limit:
                self.deactivate_function_calls()
                break  # Exit early if we reach the function call limit

        return function_call_results

    def get_system_prompt_from_llm(self) -> Optional[str]:
        return self.system_prompt

    def get_instructions_from_llm(self) -> Optional[List[str]]:
        return self.instructions
