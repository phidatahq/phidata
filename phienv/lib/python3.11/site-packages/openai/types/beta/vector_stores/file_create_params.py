# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Required, TypedDict

from ..file_chunking_strategy_param import FileChunkingStrategyParam

__all__ = ["FileCreateParams"]


class FileCreateParams(TypedDict, total=False):
    file_id: Required[str]
    """
    A [File](https://platform.openai.com/docs/api-reference/files) ID that the
    vector store should use. Useful for tools like `file_search` that can access
    files.
    """

    chunking_strategy: FileChunkingStrategyParam
    """The chunking strategy used to chunk the file(s).

    If not set, will use the `auto` strategy. Only applicable if `file_ids` is
    non-empty.
    """
