from typing import List, Iterator

from pydantic import BaseModel, ConfigDict


class LLM(BaseModel):
    model: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def response(self, messages: List) -> str:
        raise NotImplementedError

    def streaming_response(self, messages: List) -> Iterator[str]:
        raise NotImplementedError
