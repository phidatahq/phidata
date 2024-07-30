# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import Annotated

from ...._utils import PropertyInfo
from .text_delta_block import TextDeltaBlock
from .image_file_delta_block import ImageFileDeltaBlock

__all__ = ["MessageContentDelta"]

MessageContentDelta = Annotated[Union[ImageFileDeltaBlock, TextDeltaBlock], PropertyInfo(discriminator="type")]
