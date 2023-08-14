import json
from typing import List, Iterator, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict

from phi.llm.schemas import Message, Function, FunctionCall
from phi.utils.log import logger


class LLM(BaseModel):
    model: str
    name: Optional[str] = None
    metrics: Dict[str, Any] = {}

    functions: Optional[Dict[str, Function]] = None
    function_call: Optional[str] = None
    function_call_limit: int = 5
    function_call_stack: Optional[List[FunctionCall]] = None

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

    def get_function_call(self, name: str, arguments: Optional[str] = None) -> Optional[FunctionCall]:
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
                _arguments = json.loads(arguments)
                function_call.arguments = _arguments
            except Exception as e:
                logger.error(f"Unable not decode function arguments {arguments}: {e}")
                return None

        return function_call
