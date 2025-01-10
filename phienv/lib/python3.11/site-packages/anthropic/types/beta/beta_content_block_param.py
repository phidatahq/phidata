# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union
from typing_extensions import TypeAlias

from .beta_text_block_param import BetaTextBlockParam
from .beta_image_block_param import BetaImageBlockParam
from .beta_tool_use_block_param import BetaToolUseBlockParam
from .beta_base64_pdf_block_param import BetaBase64PDFBlockParam
from .beta_tool_result_block_param import BetaToolResultBlockParam

__all__ = ["BetaContentBlockParam"]

BetaContentBlockParam: TypeAlias = Union[
    BetaTextBlockParam, BetaImageBlockParam, BetaToolUseBlockParam, BetaToolResultBlockParam, BetaBase64PDFBlockParam
]
