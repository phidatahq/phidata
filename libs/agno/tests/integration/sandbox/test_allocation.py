"""Allocation intents and capacity survive replica races and lost provider replies."""

import asyncio

import pytest
import pytest_asyncio

from agno.sandbox.allocation import PostgresAllocationJournal, SandboxAllocationUnknown, SandboxCapacityExceeded
from agno.sandbox.base import SandboxError
from tests.integration.sandbox.test_postgres import URL
from tests.integration.sandbox.test_postgres import store as _store_fixture

store = _store_fixture
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="Set AGNO_TEST_SANDBOX_DB_URL")]


@pytest_asyncio.fixture
async def journal(store):
    value = PostgresAllocationJournal(store, table_name=store.bindings.name + "_alloc")
    await value.asetup()
    yield value
    await store._transaction(lambda connection: value.table.drop(connection))


async def test_only_one_replica_can_send_create(journal):
    results = await asyncio.gather(
        *(journal._reserve("e2b:deployment", "computer", "a" * 64, max_allocations=10) for _ in range(12))
    )
    assert sum(owned for _, owned in results) == 1
    assert len({row["token"] for row, _ in results}) == 1
    assert all(row["state"] == "pending" and row["provider_ref"] is None for row, _ in results)
    replacement = PostgresAllocationJournal(journal.store, table_name=journal.table.name)
    row, owned = await replacement._reserve("e2b:deployment", "computer", "a" * 64, max_allocations=10)
    assert owned is False and row["state"] == "pending"


async def test_confirmation_reconciliation_and_generation_fence(journal):
    row, owned = await journal._reserve("e2b:d", "computer", "a" * 64, max_allocations=1)
    assert owned
    with pytest.raises(SandboxAllocationUnknown):
        await journal._retire("e2b:d", "computer", row["token"], "unknown")
    await journal._bind("e2b:d", "computer", row["token"], "provider-one")
    await journal._bind("e2b:d", "computer", row["token"], "provider-one")
    with pytest.raises(SandboxAllocationUnknown):
        await journal._bind("e2b:d", "computer", row["token"], "provider-two")
    await journal._retire("e2b:d", "computer", row["token"], "provider-one")
    replacement, owned = await journal._reserve("e2b:d", "computer", "a" * 64, max_allocations=1)
    assert owned and replacement["token"] != row["token"]
    with pytest.raises(SandboxAllocationUnknown):
        await journal._bind("e2b:d", "computer", row["token"], "provider-one")
    with pytest.raises(SandboxError, match="configuration"):
        await journal._reserve("e2b:d", "computer", "b" * 64, max_allocations=1)


async def test_pending_allocations_count_toward_atomic_capacity(journal):
    async def reserve(index):
        try:
            return await journal._reserve("e2b:d", str(index), "a" * 64, max_allocations=3)
        except SandboxCapacityExceeded:
            return None

    values = await asyncio.gather(*(reserve(index) for index in range(15)))
    assert sum(value is not None for value in values) == 3
    # Independent provider/deployment namespace has its own explicitly configured quota.
    assert (await journal._reserve("modal:d", "other", "a" * 64, max_allocations=1))[1]


async def test_inspection_does_not_create_intents(journal):
    assert await journal.ainspect("e2b:d", "missing") is None


async def test_capacity_with_repeatable_read_engine(journal):
    from sqlalchemy import event

    engine = journal.store.db.db_engine
    sync_engine = getattr(engine, "sync_engine", engine)

    def repeatable_read(connection):
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

    event.listen(sync_engine, "begin", repeatable_read)
    try:
        await test_pending_allocations_count_toward_atomic_capacity(journal)
    finally:
        event.remove(sync_engine, "begin", repeatable_read)
