# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union
from typing_extensions import Literal, TypeAlias

__all__ = ["AnthropicBetaParam"]

AnthropicBetaParam: TypeAlias = Union[
    str,
    Literal[
        "message-batches-2024-09-24",
        "prompt-caching-2024-07-31",
        "computer-use-2024-10-22",
        "pdfs-2024-09-25",
        "token-counting-2024-11-01",
    ],
]
