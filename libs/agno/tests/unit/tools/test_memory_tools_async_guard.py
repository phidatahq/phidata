"""MemoryTools must fail fast on async databases instead of silently no-oping (issue #11258)."""

import pytest

from agno.db.sqlite.async_sqlite import AsyncSqliteDb
from agno.db.sqlite import SqliteDb
from agno.tools.memory import MemoryTools


def test_memory_tools_rejects_async_db():
    with pytest.raises(ValueError, match="async database"):
        MemoryTools(db=AsyncSqliteDb(db_file=":memory:"))


def test_memory_tools_accepts_sync_db(tmp_path):
    tools = MemoryTools(db=SqliteDb(db_file=str(tmp_path / "mem.db")))
    assert tools.db is not None
