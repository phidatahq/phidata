# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Optional
from typing_extensions import Literal, Required, TypedDict

__all__ = ["EmbeddingCreateParams"]


class EmbeddingCreateParams(TypedDict, total=False):
    input: Required[Union[str, List[str]]]
    """Input text to embed, encoded as a string or array of tokens.

    To embed multiple inputs in a single request, pass an array of strings or array
    of token arrays. The input must not exceed the max input tokens for the model,
    cannot be an empty string, and any array must be 2048 dimensions or less.
    """

    model: Required[Union[str, Literal["nomic-embed-text-v1_5"]]]
    """ID of the model to use."""

    encoding_format: Literal["float", "base64"]
    """The format to return the embeddings in. Can only be `float` or `base64`."""

    user: Optional[str]
    """
    A unique identifier representing your end-user, which can help us monitor and
    detect abuse.
    """
