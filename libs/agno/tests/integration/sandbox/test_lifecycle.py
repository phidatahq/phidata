"""Real recovery deletion, retirement and database deletion guards."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text, update

from agno.db.postgres import AsyncPostgresDb
from agno.db.session_resources import SessionResourcesPending
from agno.sandbox.artifacts import SandboxArtifacts, SandboxSessionNotFound
from agno.sandbox.base import SandboxError
from agno.sandbox.checkpoint import CheckpointObjectNotFound
from agno.sandbox.lifecycle import SandboxLifecycle, SandboxRecoveryDeleted
from agno.sandbox.postgres import SandboxSessionBusy
from tests.integration.sandbox.test_coordinator import IMAGE, URL, binding, run
from tests.integration.sandbox.test_coordinator import system as _system_fixture

system = _system_fixture
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not URL or not IMAGE, reason="Enable dedicated Postgres and Docker"),
]


async def delete(db, session_id, bulk=False, user_id="user"):
    method = db.delete_sessions if bulk else db.delete_session
    kwargs = {"session_ids": [session_id]} if bulk else {"session_id": session_id}
    if isinstance(db, AsyncPostgresDb):
        return await method(**kwargs, user_id=user_id)
    return await asyncio.to_thread(method, **kwargs, user_id=user_id)


async def contend_with_turn(store, operation):
    """Hold a turn's session and run locks, start operation, then take the binding as the turn would."""
    engine = create_engine(URL)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(text("SET LOCAL lock_timeout = '10s'"))
        store._hold_session(connection, "session")
        store._lock_run(connection, "first")
        task = asyncio.create_task(operation())
        await asyncio.sleep(0.5)
        await asyncio.to_thread(
            connection.execute, select(store.bindings).where(store._key("session")).with_for_update()
        )
        transaction.commit()
    finally:
        connection.close()
        engine.dispose()
    return await task


@pytest.mark.parametrize("bulk", [False, True])
async def test_session_delete_follows_turn_lock_order(system, bulk):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    await SandboxLifecycle(coordinator).adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    store = coordinator.store
    await contend_with_turn(store, lambda: delete(store.db, "session", bulk=bulk))
    assert await store._transaction(lambda c: c.execute(select(store.sessions)).first()) is None


async def test_recovery_deletion_follows_turn_lock_order(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    lifecycle = SandboxLifecycle(coordinator)
    result = await contend_with_turn(
        coordinator.store,
        lambda: lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user"),
    )
    assert result["recovery_deleted"]


async def test_stop_claim_follows_turn_lock_order(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    await contend_with_turn(
        coordinator.store,
        lambda: coordinator.store._aclaim_stop(
            agent_id=spec.agent_id,
            session_id=spec.session_id,
            user_id="user",
            run_id="first",
            queue_attempt=None,
            status="CANCELLED",
            reason="Sandbox computer retired",
        ),
    )
    assert (await binding(coordinator))["record"]["phase"] == "idle"


async def test_delete_recovery_then_conversation_and_recreated_session_starts_fresh(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    await run(coordinator, spec, "second")
    objects = list(coordinator.transfer.store.root.iterdir())
    assert len(objects) == 2
    lifecycle = SandboxLifecycle(coordinator)
    result = await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert result["conversation_retained"] and result["recovery_deleted"]
    assert all(not value.exists() for value in objects)
    retired = (await binding(coordinator))["record"]
    assert retired["phase"] == "deleted"
    assert await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user") == result
    with pytest.raises(SandboxRecoveryDeleted):
        await run(coordinator, spec, "third")
    assert await delete(coordinator.store.db, "session") is True
    # Deleting the conversation cascades the binding, so the same id starts from a fresh one.
    await run(coordinator, spec, "fourth")
    fresh = (await binding(coordinator))["record"]
    assert fresh["phase"] == "idle" and fresh["incarnation"] != retired["incarnation"]
    assert fresh["checkpoint"] and fresh["last_run_id"] == "fourth"


async def test_delete_recovery_removes_checkpoint_of_deleted_run(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    await run(coordinator, spec, "second")
    objects = list(coordinator.transfer.store.root.iterdir())
    assert len(objects) == 2
    db = coordinator.store.db
    if isinstance(db, AsyncPostgresDb):
        assert await db.delete_run("first")
    else:
        assert await asyncio.to_thread(db.delete_run, "first")
    await SandboxLifecycle(coordinator).adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert all(not value.exists() for value in objects)


async def test_delete_recovery_removes_rolled_back_staged_checkpoint(system, monkeypatch):
    coordinator, spec, _ = system
    destroy = coordinator.provider.adestroy

    async def lost_ack(handle):
        await destroy(handle)
        raise OSError("lost destroy acknowledgement")

    monkeypatch.setattr(coordinator.provider, "adestroy", lost_ack)
    with pytest.raises(OSError, match="lost destroy"):
        await run(coordinator, spec, "retired-" + uuid4().hex)
    assert (await binding(coordinator))["record"]["staged_checkpoint"]
    monkeypatch.setattr(coordinator.provider, "adestroy", destroy)
    lifecycle = SandboxLifecycle(coordinator)
    await lifecycle.aretire(spec.session_id, agent_id=spec.agent_id, user_id="user", env=spec.env)
    record = (await binding(coordinator))["record"]
    assert record["staged_checkpoint"] is None and record["checkpoint"] is None
    objects = list(coordinator.transfer.store.root.iterdir())
    assert len(objects) == 1
    await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert not objects[0].exists()


async def test_unavailable_storage_keeps_deletion_pending(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    root = coordinator.transfer.store.root
    offline = root.with_name("objects-offline")
    root.rename(offline)
    lifecycle = SandboxLifecycle(coordinator)
    with pytest.raises(CheckpointObjectNotFound):
        await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert (await binding(coordinator))["record"]["phase"] == "deleting"
    offline.rename(root)
    await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert not list(root.iterdir())


async def test_unmounted_storage_keeps_deletion_pending(system):
    coordinator, spec, tmp_path = system
    await run(coordinator, spec)
    await run(coordinator, spec, "second")
    root = coordinator.transfer.store.root
    volume = tmp_path / "volume"
    volume.mkdir()
    for path in root.iterdir():
        path.rename(volume / path.name)
    lifecycle = SandboxLifecycle(coordinator)
    for _ in range(2):
        with pytest.raises(CheckpointObjectNotFound):
            await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    record = (await binding(coordinator))["record"]
    assert record["phase"] == "deleting" and len(record["deletion_references"]) == 2
    for path in volume.iterdir():
        path.rename(root / path.name)
    await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert not list(root.iterdir())


async def test_claimed_object_on_unmounted_storage_keeps_deletion_pending(system, monkeypatch):
    coordinator, spec, tmp_path = system
    await run(coordinator, spec)
    root = coordinator.transfer.store.root
    lifecycle = SandboxLifecycle(coordinator)
    objects = coordinator.transfer.store
    original = objects.adelete

    async def crash(reference):
        raise OSError("crash before unlink")

    monkeypatch.setattr(objects, "adelete", crash)
    with pytest.raises(OSError, match="crash"):
        await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert (await binding(coordinator))["record"]["claimed_references"]
    monkeypatch.setattr(objects, "adelete", original)
    volume = tmp_path / "volume"
    volume.mkdir()
    for path in root.iterdir():
        path.rename(volume / path.name)
    with pytest.raises(CheckpointObjectNotFound):
        await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert (await binding(coordinator))["record"]["phase"] == "deleting"
    for path in volume.iterdir():
        path.rename(root / path.name)
    await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert not list(root.iterdir())


async def test_stale_session_write_cannot_strand_conversation_deletion(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    store = coordinator.store
    stale = await store._transaction(
        lambda c: c.execute(select(store.sessions.c.session_data).where(store.sessions.c.session_id == "session"))
        .scalars()
        .one()
    )
    lifecycle = SandboxLifecycle(coordinator)
    await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    await store._transaction(
        lambda c: c.execute(
            update(store.sessions).where(store.sessions.c.session_id == "session").values(session_data=stale)
        )
    )
    assert (await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user"))[
        "recovery_deleted"
    ]
    assert await delete(store.db, "session") is True


@pytest.mark.parametrize("bulk", [False, True])
async def test_ordinary_session_delete_refuses_unreleased_resources(system, bulk):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    with pytest.raises(SessionResourcesPending):
        await delete(coordinator.store.db, "session", bulk=bulk)
    assert (await binding(coordinator))["record"]["checkpoint"]
    await SandboxLifecycle(coordinator).adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    await delete(coordinator.store.db, "session", bulk=bulk)
    assert await coordinator.store._transaction(lambda c: c.execute(select(coordinator.store.sessions)).first()) is None


async def test_partial_storage_delete_is_retryable_without_restoring_execution(system, monkeypatch):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    await run(coordinator, spec, "second")
    lifecycle = SandboxLifecycle(coordinator)
    objects = coordinator.transfer.store
    original = objects.adelete
    calls = []

    async def fail_after_first(reference):
        calls.append(reference.sha256)
        if len(calls) == 2:
            raise OSError("storage outage")
        return await original(reference)

    monkeypatch.setattr(objects, "adelete", fail_after_first)
    with pytest.raises(OSError):
        await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert (await binding(coordinator))["record"]["phase"] == "deleting"
    with pytest.raises(SandboxRecoveryDeleted):
        await run(coordinator, spec, "third")
    with pytest.raises(SessionResourcesPending):
        await delete(coordinator.store.db, "session")
    monkeypatch.setattr(objects, "adelete", original)
    assert (await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user"))[
        "recovery_deleted"
    ]
    assert not list(coordinator.transfer.store.root.iterdir())


async def test_active_delete_is_refused_and_retirement_preserves_checkpoint(system):
    coordinator, spec, _ = system
    first = await run(coordinator, spec)
    task = asyncio.create_task(run(coordinator, spec, "second", config={"delay": 10}))

    async def active():
        while (await binding(coordinator))["record"]["phase"] == "idle":
            await asyncio.sleep(0.02)

    await asyncio.wait_for(active(), 10)
    lifecycle = SandboxLifecycle(coordinator)
    with pytest.raises(SandboxSessionBusy):
        await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    await lifecycle.aretire(spec.session_id, agent_id=spec.agent_id, user_id="user", env=spec.env)
    await asyncio.gather(task, return_exceptions=True)
    artifacts = SandboxArtifacts(coordinator.store, coordinator.transfer.store)
    assert (
        await artifacts.aread("fixture-effects.txt", agent_id="agent", session_id="session", user_id="user")
    ).content == (first.run_id + "\n").encode()
    assert (await binding(coordinator))["record"]["computer"] is None


async def test_delete_requires_exact_owner(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    lifecycle = SandboxLifecycle(coordinator)
    for user in (None, "attacker"):
        with pytest.raises(SandboxSessionNotFound):
            await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id=user)
    assert (await binding(coordinator))["record"]["phase"] == "idle"


async def test_foreign_checkpoint_is_not_deleted(system):
    from dataclasses import replace

    coordinator, spec, _ = system
    await run(coordinator, spec)
    await run(coordinator, replace(spec, session_id="other"), "other-run")
    rows = await coordinator.store._transaction(
        lambda c: c.execute(select(coordinator.store.bindings)).mappings().all()
    )
    foreign = next(row["record"]["checkpoint"] for row in rows if row["session_id"] == "other")
    own = next(dict(row["record"]) for row in rows if row["session_id"] == "session")
    own["checkpoint"] = foreign
    await coordinator.store._transaction(
        lambda c: c.execute(
            update(coordinator.store.bindings).where(coordinator.store._key("session")).values(record=own)
        )
    )
    with pytest.raises(SandboxError, match="another session"):
        await SandboxLifecycle(coordinator).adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert (coordinator.transfer.store.root / foreign["sha256"]).is_file()


async def test_sync_lifecycle_api_requires_sync_database(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    lifecycle = SandboxLifecycle(coordinator)
    if isinstance(coordinator.store.db, AsyncPostgresDb):
        with pytest.raises(TypeError, match="async"):
            lifecycle.delete_recovery(agent_id="agent", session_id="session", user_id="user")
    else:
        assert (
            await asyncio.to_thread(
                lifecycle.retire, spec.session_id, agent_id=spec.agent_id, user_id="user", env=spec.env
            )
        )["recovery_preserved"]
        assert (
            await asyncio.to_thread(lifecycle.delete_recovery, agent_id="agent", session_id="session", user_id="user")
        )["recovery_deleted"]


async def test_bulk_guard_is_atomic_and_scoped(system):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    store = coordinator.store
    await store._transaction(
        lambda c: c.execute(
            store.sessions.insert().values(
                session_id="ordinary",
                agent_id="agent",
                user_id="user",
                session_type="agent",
                session_data={},
                created_at=1,
            )
        )
    )
    db = store.db
    if isinstance(db, AsyncPostgresDb):
        with pytest.raises(SessionResourcesPending):
            await db.delete_sessions(["ordinary", "session"], user_id="user")
        await db.delete_sessions(["ordinary", "session"], user_id="attacker")
    else:
        with pytest.raises(SessionResourcesPending):
            await asyncio.to_thread(db.delete_sessions, ["ordinary", "session"], user_id="user")
        await asyncio.to_thread(db.delete_sessions, ["ordinary", "session"], user_id="attacker")
    assert len(await store._transaction(lambda c: c.execute(select(store.sessions)).all())) == 2


async def test_lost_deletion_commit_ack_reconciles_without_reexecution(system, monkeypatch):
    coordinator, spec, _ = system
    await run(coordinator, spec)
    lifecycle = SandboxLifecycle(coordinator)
    original = coordinator.store._transaction
    lost = []

    async def transaction(operation):
        value = await original(operation)
        if operation.__name__ == "finish" and not lost:
            lost.append(True)
            raise OSError("lost commit acknowledgement")
        return value

    monkeypatch.setattr(coordinator.store, "_transaction", transaction)
    with pytest.raises(OSError, match="acknowledgement"):
        await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user")
    assert (await lifecycle.adelete_recovery(agent_id="agent", session_id="session", user_id="user"))[
        "recovery_deleted"
    ]
    assert not list(coordinator.transfer.store.root.iterdir())
