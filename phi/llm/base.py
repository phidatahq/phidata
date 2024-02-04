from textwrap import dedent
from typing import List, Iterator, Optional, Dict, Any, Callable, Union

from pydantic import BaseModel, ConfigDict

from phi.llm.message import Message
from phi.tools import Tool, ToolRegistry
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
    response_format: Optional[Dict[str, Any]] = None

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
    # Functions extracted from the tools. Note: These are not sent to the LLM API and are only used for execution.
    functions: Optional[Dict[str, Function]] = None
    # Maximum number of function calls allowed.
    function_call_limit: int = 25
    # Stack of function calls.
    function_call_stack: Optional[List[FunctionCall]] = None

    # This setting is an experimental feature to generate tool calls from JSON mode.
    # Useful when we want to use LLMs that don't support function calls to generate tool calls.
    generate_tool_calls_from_json_mode: bool = False

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

    def add_tool(self, tool: Union[Tool, ToolRegistry, Callable, Dict, Function]) -> None:
        if self.tools is None:
            self.tools = []

        # If the tool is a Tool or Dict, add it directly to the LLM
        if isinstance(tool, Tool) or isinstance(tool, Dict):
            self.tools.append(tool)
            logger.debug(f"Added tool {tool} to LLM.")
        # If the tool is a Callable or ToolRegistry, add its functions to the LLM
        elif callable(tool) or isinstance(tool, ToolRegistry) or isinstance(tool, Function):
            if self.functions is None:
                self.functions = {}

            if isinstance(tool, ToolRegistry):
                self.functions.update(tool.functions)
                for func in tool.functions.values():
                    self.tools.append({"type": "function", "function": func.to_dict()})
                logger.debug(f"Functions from {tool.name} added to LLM.")
            elif isinstance(tool, Function):
                self.functions[tool.name] = tool
                self.tools.append({"type": "function", "function": tool.to_dict()})
                logger.debug(f"Function {tool.name} added to LLM.")
            elif callable(tool):
                func = Function.from_callable(tool)
                self.functions[func.name] = func
                self.tools.append({"type": "function", "function": func.to_dict()})
                logger.debug(f"Function {func.name} added to LLM.")

    def run_function_calls(self, function_calls: List[FunctionCall], role: str = "tool") -> List[Message]:
        function_call_results: List[Message] = []
        for function_call in function_calls:
            if self.function_call_stack is None:
                self.function_call_stack = []

            # -*- Check function call limit
            if len(self.function_call_stack) > self.function_call_limit:
                # Set future tool calls to "none" if the function call limit is exceeded.
                self.tool_choice = "none"
                function_call_results.append(
                    Message(
                        role=role,
                        tool_call_id=function_call.call_id,
                        content=f"Tool call limit ({self.function_call_limit}) exceeded.",
                    )
                )
                continue

            # -*- Run function call
            self.function_call_stack.append(function_call)
            _function_call_timer = Timer()
            _function_call_timer.start()
            function_call.execute()
            _function_call_timer.stop()
            _function_call_result = Message(
                role=role,
                tool_call_id=function_call.call_id,
                content=function_call.result,
                metrics={"time": _function_call_timer.elapsed},
            )
            if "tool_call_times" not in self.metrics:
                self.metrics["tool_call_times"] = {}
            if function_call.function.name not in self.metrics["tool_call_times"]:
                self.metrics["tool_call_times"][function_call.function.name] = []
            self.metrics["tool_call_times"][function_call.function.name].append(_function_call_timer.elapsed)
            function_call_results.append(_function_call_result)
        return function_call_results

    def get_instructions_to_generate_tool_calls(self) -> List[str]:
        if self.functions is not None:
            return [
                "You can select one or more of the above tools to achieve your task.",
                "If a tool is found, you must respond in the JSON format matching the following schema:\n"
                + dedent(
                    """\
                    {{
                        "tool_calls": [{
                            "name": "<name of the selected tool>",
                            "arguments": <parameters for the selected tool, matching the tool's JSON schema
                        }]
                    }}\
                    """
                ),
                "Do not add any additional Notes or Explanations",
                "REMEMBER: IF YOU USE A TOOL, YOU MUST RESPOND IN THE JSON FORMAT. START YOUR RESPONSE WITH '{' AND END IT WITH '}'.",
            ]
        return []

    def get_prompt_with_tool_calls(self) -> Optional[str]:
        if self.functions is not None:
            _tool_choice_prompt = "You have access to the following tools:"
            for _f_name, _function in self.functions.items():
                _function_json = _function.get_json_schema()
                if _function_json:
                    _tool_choice_prompt += f"\n{_function_json}"
            _tool_choice_prompt += "\n\n"
            return _tool_choice_prompt
        return None
