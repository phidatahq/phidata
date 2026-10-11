"""Regression tests for #10932: Knowledge.search(search_type=...) must not leak.

A per-call ``search_type`` override must not permanently mutate the shared
``vector_db.search_type``.  After an overridden call returns (or raises), the
next caller must see the original search type.
"""

from typing import Any, Dict, List, Optional

import pytest

from agno.knowledge.document import Document
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.base import VectorDb
from agno.vectordb.search import SearchType


class _RecordingVdb(VectorDb):
    """A stub vector db that records the search_type seen on every call."""

    def __init__(self) -> None:
        self.search_type: SearchType = SearchType.vector
        self.seen: List[str] = []

    # -- write/structural (no-ops) -------------------------------------------
    def create(self) -> None: ...
    async def async_create(self) -> None: ...
    def name_exists(self, name: str) -> bool:
        return False

    async def async_name_exists(self, name: str) -> bool:
        return False

    def id_exists(self, id: str) -> bool:
        return False

    def content_hash_exists(self, content_hash: str, user_id: Optional[str] = None) -> bool:
        return False

    def upsert_available(self) -> bool:
        return False

    def insert(
        self, content_hash: str, documents: List[Document], filters=None, user_id: Optional[str] = None
    ) -> None: ...
    async def async_insert(
        self, content_hash: str, documents: List[Document], filters=None, user_id: Optional[str] = None
    ) -> None: ...
    def upsert(
        self, content_hash: str, documents: List[Document], filters=None, user_id: Optional[str] = None
    ) -> None: ...
    async def async_upsert(
        self, content_hash: str, documents: List[Document], filters=None, user_id: Optional[str] = None
    ) -> None: ...

    def drop(self) -> None: ...
    async def async_drop(self) -> None: ...
    def exists(self) -> bool:
        return True

    async def async_exists(self) -> bool:
        return True

    def delete(self) -> bool:
        return True

    def delete_by_id(self, id: str) -> bool:
        return True

    def delete_by_name(self, name: str) -> bool:
        return True

    def delete_by_metadata(self, metadata: Dict[str, Any]) -> None: ...
    def update_metadata(self, content_id: str, metadata: Dict[str, Any]) -> None: ...
    def delete_by_content_id(self, content_id: str, user_id: Optional[str] = None) -> bool:
        return True

    def get_supported_search_types(self) -> List[str]:
        return ["vector", "keyword", "hybrid"]

    # -- search records the search_type it observes --------------------------
    def search(self, query: str, limit: int = 5, filters=None, user_id: Optional[str] = None) -> List[Document]:
        self.seen.append(str(self.search_type))
        return []

    async def async_search(
        self, query: str, limit: int = 5, filters=None, user_id: Optional[str] = None
    ) -> List[Document]:
        self.seen.append(str(self.search_type))
        return []


# ---------------------------------------------------------------------------
# Sync search()
# ---------------------------------------------------------------------------


class TestSearchTypeRestoreSync:
    def test_override_does_not_leak_to_subsequent_calls(self):
        vdb = _RecordingVdb()
        kb = Knowledge(vector_db=vdb)

        kb.search("hello")  # default -> vector
        kb.search("world", search_type="keyword")  # override -> keyword
        kb.search("again")  # should see vector again

        assert vdb.seen == ["SearchType.vector", "SearchType.keyword", "SearchType.vector"], (
            f"search_type leaked: {vdb.seen}"
        )

    def test_override_still_applies_during_call(self):
        vdb = _RecordingVdb()
        kb = Knowledge(vector_db=vdb)

        kb.search("q", search_type="hybrid")

        assert vdb.seen == ["SearchType.hybrid"], "override must take effect for the call itself"

    def test_restore_after_exception(self):
        vdb = _RecordingVdb()
        kb = Knowledge(vector_db=vdb)

        # Make the vector db raise during search; Knowledge catches and returns []
        def boom(*a, **kw):
            raise RuntimeError("backend exploded")

        vdb.search = boom  # type: ignore[method-assign]

        result = kb.search("q", search_type="keyword")

        assert result == []  # Knowledge swallows the error
        # Even though search raised, search_type must be restored
        assert vdb.search_type == SearchType.vector, f"search_type not restored after exception: {vdb.search_type}"

    def test_no_override_leaves_state_untouched(self):
        vdb = _RecordingVdb()
        kb = Knowledge(vector_db=vdb)

        kb.search("a")
        kb.search("b")

        assert vdb.search_type == SearchType.vector
        assert vdb.seen == ["SearchType.vector", "SearchType.vector"]


# ---------------------------------------------------------------------------
# Async asearch()
# ---------------------------------------------------------------------------


class TestSearchTypeRestoreAsync:
    async def test_async_override_does_not_leak(self):
        vdb = _RecordingVdb()
        kb = Knowledge(vector_db=vdb)

        await kb.asearch("hello")
        await kb.asearch("world", search_type="keyword")
        await kb.asearch("again")

        assert vdb.seen == ["SearchType.vector", "SearchType.keyword", "SearchType.vector"], (
            f"async search_type leaked: {vdb.seen}"
        )

    async def test_async_restore_after_exception(self):
        vdb = _RecordingVdb()
        kb = Knowledge(vector_db=vdb)

        async def boom(*a, **kw):
            raise RuntimeError("async backend exploded")

        vdb.async_search = boom  # type: ignore[method-assign]

        result = await kb.asearch("q", search_type="keyword")

        assert result == []  # Knowledge swallows the error
        assert vdb.search_type == SearchType.vector, (
            f"async search_type not restored after exception: {vdb.search_type}"
        )
