# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Optional

from ..._models import BaseModel

__all__ = ["BetaUsage"]


class BetaUsage(BaseModel):
    cache_creation_input_tokens: Optional[int] = None
    """The number of input tokens used to create the cache entry."""

    cache_read_input_tokens: Optional[int] = None
    """The number of input tokens read from the cache."""

    input_tokens: int
    """The number of input tokens which were used."""

    output_tokens: int
    """The number of output tokens which were used."""
