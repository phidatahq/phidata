# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.


from ..._models import BaseModel

__all__ = ["BetaMessageDeltaUsage"]


class BetaMessageDeltaUsage(BaseModel):
    output_tokens: int
    """The cumulative number of output tokens which were used."""
