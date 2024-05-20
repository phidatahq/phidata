# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union

from .chat_completion_content_part_text_param import ChatCompletionContentPartTextParam
from .chat_completion_content_part_image_param import ChatCompletionContentPartImageParam

__all__ = ["ChatCompletionContentPartParam"]

ChatCompletionContentPartParam = Union[ChatCompletionContentPartTextParam, ChatCompletionContentPartImageParam]
