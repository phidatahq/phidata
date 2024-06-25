# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Literal, Required, TypedDict

from ...types import shared_params

__all__ = ["FunctionToolParam"]


class FunctionToolParam(TypedDict, total=False):
    function: Required[shared_params.FunctionDefinition]

    type: Required[Literal["function"]]
    """The type of tool being defined: `function`"""
