import json
from typing import List, Iterator, Optional, Dict, Any, Callable, Union

from pydantic import BaseModel, ConfigDict

from phi.llm.schemas import Message, Function, FunctionCall
from phi.llm.agent.base import BaseAgent
from phi.llm.tool.base import BaseTool
from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class LLM(BaseModel):
    # ID of the model to use.
    model: str
    # Name for this LLM (not used for api calls).
    name: Optional[str] = None
    # Metrics collected for this LLM (not used for api calls).
    metrics: Dict[str, Any] = {}

    # A list of tools the model may call.
    # Currently, only functions are supported as a tool.
    # Use this to provide a list of functions the model may generate JSON inputs for.
    tools: Optional[List[BaseTool]] = None
    # Controls which (if any) function is called by the model.
    # "none" means the model will not call a function and instead generates a message.
    # "auto" means the model can pick between generating a message or calling a function.
    # Specifying a particular function via {"type: "function", "function": {"name": "my_function"}}
    #   forces the model to call that function.
    # "none" is the default when no functions are present. "auto" is the default if functions are present.
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    # A list of functions to add to the tools
    functions: Optional[Dict[str, Function]] = None

    # Maximum number of function calls allowed.
    function_call_limit: int = 50
    # Stack of function calls.
    function_call_stack: Optional[List[FunctionCall]] = None
    # If True, shows function calls in the response.
    show_function_calls: Optional[bool] = None
    # If True, runs function calls before sending back the response content.
    run_function_calls: bool = True

    # NOTE: Deprecated in favor of tool_choice.
    function_call: Optional[str] = None

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

    def add_function(self, f: Callable) -> None:
        func = Function.from_callable(f)
        if self.functions is None:
            self.functions = {}
        self.functions[func.name] = func
        logger.debug(f"Added function {func.name} to LLM.")

    def add_function_schema(self, func: Function, if_not_exists: bool = True) -> None:
        if self.functions is None:
            self.functions = {}

        if if_not_exists and func.name in self.functions:
            return

        self.functions[func.name] = func
        logger.debug(f"Added function {func.name} to LLM.")

    def add_function_registry(self, registry: FunctionRegistry) -> None:
        if self.functions is None:
            self.functions = {}

        self.functions.update(registry.functions)
        logger.debug(f"Functions from {registry.name} added to LLM.")

    def add_agent(self, agent: BaseAgent) -> None:
        if self.functions is None:
            self.functions = {}

        self.functions.update(agent.functions)
        logger.debug(f"Agent: {agent.name} added to LLM.")

    def get_function_call(self, name: str, arguments: Optional[str] = None) -> Optional[FunctionCall]:
        logger.debug(f"Getting function {name}. Args: {arguments}")
        if self.functions is None:
            return None

        function_to_call: Optional[Function] = None
        if name in self.functions:
            function_to_call = self.functions[name]
        if function_to_call is None:
            logger.error(f"Function {name} not found")
            return None

        function_call = FunctionCall(function=function_to_call)
        if arguments is not None and arguments != "":
            try:
                if "None" in arguments:
                    arguments = arguments.replace("None", "null")
                if "True" in arguments:
                    arguments = arguments.replace("True", "true")
                if "False" in arguments:
                    arguments = arguments.replace("False", "false")
                _arguments = json.loads(arguments)
            except Exception as e:
                logger.error(f"Unable to decode function arguments {arguments}: {e}")
                return None

            if not isinstance(_arguments, dict):
                logger.error(f"Function arguments {arguments} is not a valid JSON object")
                return None

            try:
                clean_arguments: Dict[str, Any] = {}
                for k, v in _arguments.items():
                    if isinstance(v, str):
                        _v = v.strip().lower()
                        if _v in ("none", "null"):
                            clean_arguments[k] = None
                        elif _v == "true":
                            clean_arguments[k] = True
                        elif _v == "false":
                            clean_arguments[k] = False
                        else:
                            clean_arguments[k] = v.strip()
                    else:
                        clean_arguments[k] = v

                function_call.arguments = clean_arguments
            except Exception as e:
                logger.error(f"Unable to parse function arguments {arguments}: {e}")
                return None

        return function_call
