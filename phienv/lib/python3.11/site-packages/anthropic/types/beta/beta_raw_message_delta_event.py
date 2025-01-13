# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Optional
from typing_extensions import Literal

from ..._models import BaseModel
from .beta_message_delta_usage import BetaMessageDeltaUsage

__all__ = ["BetaRawMessageDeltaEvent", "Delta"]


class Delta(BaseModel):
    stop_reason: Optional[Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]] = None

    stop_sequence: Optional[str] = None


class BetaRawMessageDeltaEvent(BaseModel):
    delta: Delta

    type: Literal["message_delta"]

    usage: BetaMessageDeltaUsage
    """Billing and rate-limit usage.

    Anthropic's API bills and rate-limits by token counts, as tokens represent the
    underlying cost to our systems.

    Under the hood, the API transforms requests into a format suitable for the
    model. The model's output then goes through a parsing stage before becoming an
    API response. As a result, the token counts in `usage` will not match one-to-one
    with the exact visible content of an API request or response.

    For example, `output_tokens` will be non-zero, even for an empty string response
    from Claude.
    """
