from typing import List, Iterator, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class LLM(BaseModel):
    model: str
    name: Optional[str] = None
    metrics: Dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def response(self, messages: List) -> str:
        raise NotImplementedError

    def response_stream(self, messages: List) -> Iterator[str]:
        raise NotImplementedError
