# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import Literal

from .assistant_response_format import AssistantResponseFormat

__all__ = ["AssistantResponseFormatOption"]

AssistantResponseFormatOption = Union[Literal["none", "auto"], AssistantResponseFormat]
