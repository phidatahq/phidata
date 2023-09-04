import json
from typing import List, Iterator, Optional, Dict, Any, Callable

from pydantic import BaseModel, ConfigDict

from phi.llm.schemas import Message, Function, FunctionCall
from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class LLM(BaseModel):
    model: str
    name: Optional[str] = None
    metrics: Dict[str, Any] = {}

    functions: Optional[Dict[str, Function]] = None
    function_call: Optional[str] = None
    function_call_limit: int = 50
    function_call_stack: Optional[List[FunctionCall]] = None
    show_function_calls: Optional[bool] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def response(self, messages: List[Message]) -> str:
        raise NotImplementedError

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(exclude_none=True, exclude={"functions", "function_call", "function_call_stack"})
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

    def add_function_registry(self, registry: FunctionRegistry) -> None:
        if self.functions is None:
            self.functions = {}

        self.functions.update(registry.functions)
        logger.debug(f"Functions from {registry.name} added to LLM.")

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
