from typing import List, Iterator, Optional

from pydantic import BaseModel, ConfigDict


class LLM(BaseModel):
    model: str
    name: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def response(self, messages: List) -> str:
        raise NotImplementedError

    def streaming_response(self, messages: List) -> Iterator[str]:
        raise NotImplementedError
