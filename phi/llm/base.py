from typing import List, Iterator, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict

from phi.llm.schemas import Message, Function


class LLM(BaseModel):
    model: str
    name: Optional[str] = None
    metrics: Dict[str, Any] = {}

    functions: Optional[List[Function]] = None
    function_call: Optional[str] = None
    function_call_limit: int = 5

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def response(self, messages: List[Message]) -> str:
        raise NotImplementedError

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(exclude_none=True, exclude={"functions"})
        if self.functions:
            _dict["functions"] = [f.to_dict() for f in self.functions]
        return _dict
