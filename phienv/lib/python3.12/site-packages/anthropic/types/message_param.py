# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union, Iterable
from typing_extensions import Literal, Required, TypedDict

from .content_block import ContentBlock
from .text_block_param import TextBlockParam
from .image_block_param import ImageBlockParam
from .document_block_param import DocumentBlockParam
from .tool_use_block_param import ToolUseBlockParam
from .tool_result_block_param import ToolResultBlockParam

__all__ = ["MessageParam"]


class MessageParam(TypedDict, total=False):
    content: Required[
        Union[
            str,
            Iterable[
                Union[
                    TextBlockParam,
                    ImageBlockParam,
                    ToolUseBlockParam,
                    ToolResultBlockParam,
                    DocumentBlockParam,
                    ContentBlock,
                ]
            ],
        ]
    ]

    role: Required[Literal["user", "assistant"]]
