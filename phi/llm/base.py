from typing import List, Iterator, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, field_validator, Field


class LLM(BaseModel):
    model: str
    name: Optional[str] = Field(None, validate_default=True)
    usage_data: Dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("name", mode="before")
    def update_name(cls, v):
        return v or cls.__class__.__name__

    def response(self, messages: List) -> str:
        raise NotImplementedError

    def streaming_response(self, messages: List) -> Iterator[str]:
        raise NotImplementedError
