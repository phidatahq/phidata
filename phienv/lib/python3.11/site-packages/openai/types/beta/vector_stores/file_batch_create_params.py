# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List
from typing_extensions import Required, TypedDict

from ..file_chunking_strategy_param import FileChunkingStrategyParam

__all__ = ["FileBatchCreateParams"]


class FileBatchCreateParams(TypedDict, total=False):
    file_ids: Required[List[str]]
    """
    A list of [File](https://platform.openai.com/docs/api-reference/files) IDs that
    the vector store should use. Useful for tools like `file_search` that can access
    files.
    """

    chunking_strategy: FileChunkingStrategyParam
    """The chunking strategy used to chunk the file(s).

    If not set, will use the `auto` strategy. Only applicable if `file_ids` is
    non-empty.
    """
