from typing import List, Iterator, Optional, Dict, Any, Callable, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationInfo

from phi.model.message import Message
from phi.model.response import ModelResponse, ModelResponseEvent
from phi.tools import Tool, Toolkit
from phi.tools.function import Function, FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer


class Model(BaseModel):
    # ID of the model to use.
    id: str = Field(..., alias="model")
    # Name for this Model. This is not sent to the Model API.
    name: Optional[str] = None
    # Provider for this Model. This is not sent to the Model API.
    provider: Optional[str] = Field(None, validate_default=True)
    # Metrics collected for this Model. This is not sent to the Model API.
    metrics: Dict[str, Any] = Field(default_factory=dict)
    response_format: Optional[Any] = None

    # A list of tools provided to the Model.
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
    # Maximum number of tool calls allowed.
    tool_call_limit: Optional[int] = None

    # -*- Functions available to the Model to call -*-
    # Functions extracted from the tools.
    # Note: These are not sent to the Model API and are only used for execution + deduplication.
    functions: Optional[Dict[str, Function]] = None
    # Function call stack.
    function_call_stack: Optional[List[FunctionCall]] = None

    # System prompt from the model added to the Agent.
    system_prompt: Optional[str] = None
    # Instructions from the model added to the Agent.
    instructions: Optional[List[str]] = None

    # Session ID of the calling Agent or Workflow.
    session_id: Optional[str] = None
    # Whether to use the structured outputs with this Model.
    structured_outputs: Optional[bool] = None
    # Whether the Model supports structured outputs.
    supports_structured_outputs: bool = False
    # Whether to add images to the message content.
    add_images_to_message_content: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    @field_validator("provider", mode="before")
    def set_provider(cls, v: Optional[str], info: ValidationInfo) -> str:
        model_name = info.data.get("name")
        model_id = info.data.get("id")
        return v or f"{model_name} ({model_id})"

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(include={"name", "id", "provider", "metrics"})
        if self.functions:
            _dict["functions"] = {k: v.to_dict() for k, v in self.functions.items()}
            _dict["tool_call_limit"] = self.tool_call_limit
        return _dict

    def invoke(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    async def ainvoke(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def invoke_stream(self, *args, **kwargs) -> Iterator[Any]:
        raise NotImplementedError

    async def ainvoke_stream(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def response(self, messages: List[Message]) -> ModelResponse:
        raise NotImplementedError

    async def aresponse(self, messages: List[Message]) -> ModelResponse:
        raise NotImplementedError

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        raise NotImplementedError

    async def aresponse_stream(self, messages: List[Message]) -> Any:
        raise NotImplementedError

    def _log_messages(self, messages: List[Message]) -> None:
        """
        Log messages for debugging.
        """
        for m in messages:
            m.log()

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

    def add_tool(self, tool: Union[Tool, Toolkit, Callable, Dict, Function], structured_outputs: bool = False) -> None:
        if self.tools is None:
            self.tools = []

        # If the tool is a Tool or Dict, add it directly to the Model
        if isinstance(tool, Tool) or isinstance(tool, Dict):
            if tool not in self.tools:
                self.tools.append(tool)
                logger.debug(f"Added tool {tool} to model.")

        # If the tool is a Callable or Toolkit, add its functions to the Model
        elif callable(tool) or isinstance(tool, Toolkit) or isinstance(tool, Function):
            if self.functions is None:
                self.functions = {}

            if isinstance(tool, Toolkit):
                # For each function in the toolkit
                for name, func in tool.functions.items():
                    # If the function does not exist in self.functions, add to self.tools
                    if name not in self.functions:
                        if structured_outputs and self.supports_structured_outputs:
                            func.strict = True
                        self.functions[name] = func
                        self.tools.append({"type": "function", "function": func.to_dict()})
                        logger.debug(f"Function {name} from {tool.name} added to model.")

            elif isinstance(tool, Function):
                if tool.name not in self.functions:
                    if structured_outputs and self.supports_structured_outputs:
                        tool.strict = True
                    self.functions[tool.name] = tool
                    self.tools.append({"type": "function", "function": tool.to_dict()})
                    logger.debug(f"Function {tool.name} added to model.")

            elif callable(tool):
                try:
                    function_name = tool.__name__
                    if function_name not in self.functions:
                        func = Function.from_callable(tool)
                        if structured_outputs and self.supports_structured_outputs:
                            func.strict = True
                        self.functions[func.name] = func
                        self.tools.append({"type": "function", "function": func.to_dict()})
                        logger.debug(f"Function {func.name} added to Model.")
                except Exception as e:
                    logger.warning(f"Could not add function {tool}: {e}")

    def deactivate_function_calls(self) -> None:
        # Deactivate tool calls by setting future tool calls to "none"
        # This is triggered when the function call limit is reached.
        self.tool_choice = "none"

    def run_function_calls(
        self, function_calls: List[FunctionCall], function_call_results: List[Message], tool_role: str = "tool"
    ) -> Iterator[ModelResponse]:
        for function_call in function_calls:
            if self.function_call_stack is None:
                self.function_call_stack = []

            # -*- Start function call
            _function_call_timer = Timer()
            _function_call_timer.start()
            yield ModelResponse(
                content=function_call.get_call_str(),
                tool_call={
                    "role": tool_role,
                    "tool_call_id": function_call.call_id,
                    "tool_name": function_call.function.name,
                    "tool_args": function_call.arguments,
                },
                event=ModelResponseEvent.tool_call_started.value,
            )

            # -*- Run function call
            function_call_success = function_call.execute()
            _function_call_timer.stop()

            _function_call_result = Message(
                role=tool_role,
                content=function_call.result if function_call_success else function_call.error,
                tool_call_id=function_call.call_id,
                tool_name=function_call.function.name,
                tool_args=function_call.arguments,
                tool_call_error=not function_call_success,
                metrics={"time": _function_call_timer.elapsed},
            )
            yield ModelResponse(
                content=f"{function_call.get_call_str()} completed in {_function_call_timer.elapsed:.4f}s.",
                tool_call=_function_call_result.model_dump(
                    include={
                        "content",
                        "tool_call_id",
                        "tool_name",
                        "tool_args",
                        "tool_call_error",
                        "metrics",
                        "created_at",
                    }
                ),
                event=ModelResponseEvent.tool_call_completed.value,
            )

            # Add metrics to the model
            if "tool_call_times" not in self.metrics:
                self.metrics["tool_call_times"] = {}
            if function_call.function.name not in self.metrics["tool_call_times"]:
                self.metrics["tool_call_times"][function_call.function.name] = []
            self.metrics["tool_call_times"][function_call.function.name].append(_function_call_timer.elapsed)

            # Add the function call result to the function call results
            function_call_results.append(_function_call_result)
            self.function_call_stack.append(function_call)

            # -*- Check function call limit
            if self.tool_call_limit and len(self.function_call_stack) >= self.tool_call_limit:
                self.deactivate_function_calls()
                break  # Exit early if we reach the function call limit

    def get_system_message_for_model(self) -> Optional[str]:
        return self.system_prompt

    def get_instructions_for_model(self) -> Optional[List[str]]:
        return self.instructions

    def clear(self) -> None:
        """Clears the Model's state."""

        self.metrics = {}
        self.functions = None
        self.function_call_stack = None
        self.session_id = None

    def deep_copy(self, *, update: Optional[Dict[str, Any]] = None) -> "Model":
        new_model = self.model_copy(deep=True, update=update)
        # Clear the new model to remove any references to the old model
        new_model.clear()
        return new_model
