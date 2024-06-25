# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing_extensions import Literal

__all__ = ["RunStatus"]

RunStatus = Literal[
    "queued", "in_progress", "requires_action", "cancelling", "cancelled", "failed", "completed", "expired"
]
