# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union
from typing_extensions import TypeAlias

from .text_block_param import TextBlockParam
from .image_block_param import ImageBlockParam
from .document_block_param import DocumentBlockParam
from .tool_use_block_param import ToolUseBlockParam
from .tool_result_block_param import ToolResultBlockParam

__all__ = ["ContentBlockParam"]

ContentBlockParam: TypeAlias = Union[
    TextBlockParam, ImageBlockParam, ToolUseBlockParam, ToolResultBlockParam, DocumentBlockParam
]
