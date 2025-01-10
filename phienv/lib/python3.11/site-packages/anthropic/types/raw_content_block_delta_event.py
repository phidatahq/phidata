# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import Literal, TypeAlias

from .._models import BaseModel
from .text_delta import TextDelta
from .input_json_delta import InputJSONDelta

__all__ = ["RawContentBlockDeltaEvent", "Delta"]

Delta: TypeAlias = Union[TextDelta, InputJSONDelta]


class RawContentBlockDeltaEvent(BaseModel):
    delta: Delta

    index: int

    type: Literal["content_block_delta"]
