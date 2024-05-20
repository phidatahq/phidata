# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Optional
from typing_extensions import Literal

from ..._models import BaseModel

__all__ = ["AssistantResponseFormat"]


class AssistantResponseFormat(BaseModel):
    type: Optional[Literal["text", "json_object"]] = None
    """Must be one of `text` or `json_object`."""
