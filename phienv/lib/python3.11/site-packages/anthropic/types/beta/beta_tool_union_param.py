# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union
from typing_extensions import TypeAlias

from .beta_tool_param import BetaToolParam
from .beta_tool_bash_20241022_param import BetaToolBash20241022Param
from .beta_tool_text_editor_20241022_param import BetaToolTextEditor20241022Param
from .beta_tool_computer_use_20241022_param import BetaToolComputerUse20241022Param

__all__ = ["BetaToolUnionParam"]

BetaToolUnionParam: TypeAlias = Union[
    BetaToolParam, BetaToolComputerUse20241022Param, BetaToolBash20241022Param, BetaToolTextEditor20241022Param
]
