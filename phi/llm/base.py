from typing import List, Iterator, Optional, Dict, Any, Callable, Union

from pydantic import BaseModel, ConfigDict

from phi.llm.message import Message
from phi.tools import Tool, ToolRegistry
from phi.tools.function import Function, FunctionCall
from phi.utils.log import logger


class LLM(BaseModel):
    # ID of the model to use.
    model: str
    # Name for this LLM. Note: This is not sent to the LLM API.
    name: Optional[str] = None
    # Metrics collected for this LLM. Note: This is not sent to the LLM API.
    metrics: Dict[str, Any] = {}

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

    # -*- Functions available to the LLM to call -*-
    # Functions provided from the tools. Note: These are not sent to the LLM API.
    functions: Optional[Dict[str, Function]] = None
    # If True, runs function calls before sending back the response content.
    run_function_calls: bool = True
    # If True, shows function calls in the response.
    show_function_calls: Optional[bool] = None
    # Maximum number of function calls allowed.
    function_call_limit: int = 25
    # Stack of function calls.
    function_call_stack: Optional[List[FunctionCall]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        raise NotImplementedError

    def invoke_model(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def invoke_model_stream(self, *args, **kwargs) -> Iterator[Any]:
        raise NotImplementedError

    def parsed_response(self, messages: List[Message]) -> str:
        raise NotImplementedError

    def response_message(self, messages: List[Message]) -> Dict:
        raise NotImplementedError

    def parsed_response_stream(self, messages: List[Message]) -> Iterator[str]:
        raise NotImplementedError

    def response_delta(self, messages: List[Message]) -> Iterator[Dict]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(include={"model", "name", "metrics"})
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

    def add_tool(self, tool: Union[Tool, ToolRegistry, Callable, Dict]) -> None:
        if self.tools is None:
            self.tools = []

        # If the tool is a Tool or Dict, add it directly to the LLM
        if isinstance(tool, Tool) or isinstance(tool, Dict):
            self.tools.append(tool)
            logger.debug(f"Added tool {tool} to LLM.")

        # If the tool is a Callable or ToolRegistry, add its functions to the LLM
        if callable(tool) or isinstance(tool, ToolRegistry):
            if self.functions is None:
                self.functions = {}

            if isinstance(tool, ToolRegistry):
                self.functions.update(tool.functions)
                for func in tool.functions.values():
                    self.tools.append({"type": "function", "function": func.to_dict()})
                logger.debug(f"Functions from {tool.name} added to LLM.")
            elif callable(tool):
                func = Function.from_callable(tool)
                self.functions[func.name] = func
                self.tools.append({"type": "function", "function": func.to_dict()})
                logger.debug(f"Function {func.name} added to LLM.")
