# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import Annotated, TypeAlias

from ..._utils import PropertyInfo
from .beta_text_block import BetaTextBlock
from .beta_tool_use_block import BetaToolUseBlock

__all__ = ["BetaContentBlock"]

BetaContentBlock: TypeAlias = Annotated[Union[BetaTextBlock, BetaToolUseBlock], PropertyInfo(discriminator="type")]
