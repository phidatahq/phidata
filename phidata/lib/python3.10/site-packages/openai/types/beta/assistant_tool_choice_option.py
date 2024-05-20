# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import Literal

from .assistant_tool_choice import AssistantToolChoice

__all__ = ["AssistantToolChoiceOption"]

AssistantToolChoiceOption = Union[Literal["none", "auto"], AssistantToolChoice]
