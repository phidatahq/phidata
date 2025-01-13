# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Optional

from .._models import BaseModel

__all__ = ["CompletionUsage"]


class CompletionUsage(BaseModel):
    completion_tokens: int
    """Number of tokens in the generated completion."""

    prompt_tokens: int
    """Number of tokens in the prompt."""

    total_tokens: int
    """Total number of tokens used in the request (prompt + completion)."""

    completion_time: Optional[float] = None
    """Time spent generating tokens"""

    prompt_time: Optional[float] = None
    """Time spent processing input tokens"""

    queue_time: Optional[float] = None
    """Time the requests was spent queued"""

    total_time: Optional[float] = None
    """completion time and prompt time combined"""
