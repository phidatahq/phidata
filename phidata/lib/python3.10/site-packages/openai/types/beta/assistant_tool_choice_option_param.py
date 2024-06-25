# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union
from typing_extensions import Literal

from .assistant_tool_choice_param import AssistantToolChoiceParam

__all__ = ["AssistantToolChoiceOptionParam"]

AssistantToolChoiceOptionParam = Union[Literal["none", "auto"], AssistantToolChoiceParam]
