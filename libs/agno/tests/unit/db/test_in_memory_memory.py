"""Unit tests for InMemoryDb memory operations."""

import pytest

from agno.db.in_memory.in_memory_db import InMemoryDb
from agno.db.schemas.memory import UserMemory


@pytest.fixture
def db():
    db = InMemoryDb()
    db._memories = [
        {"memory_id": "m1", "user_id": "alice", "memory": "alice thing", "topics": ["pref", "ui"]},
        {"memory_id": "m2", "user_id": "bob", "memory": "bob thing", "topics": ["code", "ts"]},
    ]
    return db


class TestGetAllMemoryTopicsIsolation:
    def test_returns_all_topics_when_no_user_filter(self, db):
        assert set(db.get_all_memory_topics()) == {"pref", "ui", "code", "ts"}

    def test_returns_only_own_topics_when_filtered_by_user(self, db):
        assert set(db.get_all_memory_topics(user_id="alice")) == {"pref", "ui"}
        assert set(db.get_all_memory_topics(user_id="bob")) == {"code", "ts"}

    def test_returns_empty_for_unknown_user(self, db):
        assert db.get_all_memory_topics(user_id="nobody") == []


class TestUserMemoryAliasing:
    def test_upsert_user_memory_isolates_caller_topics_mutation(self):
        db = InMemoryDb()
        original = UserMemory(memory="remember this", topics=["saved-topic"])
        db.upsert_user_memory(original)

        assert original.topics is not None
        original.topics.append("unsaved-topic")

        stored = db.get_user_memory(original.memory_id)
        assert stored is not None
        assert stored.topics == ["saved-topic"]
        assert "unsaved-topic" not in stored.topics
        assert db.get_all_memory_topics() == ["saved-topic"]

    def test_upsert_user_memories_isolates_caller_topics_mutation(self):
        db = InMemoryDb()
        original = UserMemory(memory="remember this too", topics=["saved-topic"])
        db.upsert_memories([original])

        assert original.topics is not None
        original.topics.append("unsaved-topic")

        stored = db.get_user_memory(original.memory_id)
        assert stored is not None
        assert stored.topics == ["saved-topic"]
        assert "unsaved-topic" not in stored.topics
        assert db.get_all_memory_topics() == ["saved-topic"]
