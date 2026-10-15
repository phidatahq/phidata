"""Real PostgreSQL fencing and atomic recovery publication; no model calls."""

import asyncio
import threading
import os
import time
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.sandbox.base import SandboxError, SandboxHandle
from agno.sandbox.checkpoint import CheckpointRef
from agno.sandbox.postgres import (
    SandboxLeaseLost,
    SandboxRunFinished,
    SandboxSessionBusy,
    _SandboxStore,
)
from agno.session import AgentSession
from sqlalchemy import create_engine, delete, event, func, select, text, update

URL = os.environ.get("AGNO_TEST_SANDBOX_DB_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="Set AGNO_TEST_SANDBOX_DB_URL")]
REF = CheckpointRef("a" * 64, 10240)


@pytest_asyncio.fixture(params=[PostgresDb, AsyncPostgresDb])
async def store(request):
    db = new_db(request.param, uuid4().hex[:12])
    store = _SandboxStore(db)
    yield store
    await store._transaction(lambda c: [table.drop(c) for table in (store.bindings, store.runs, store.sessions)])
    await dispose(db)


def new_db(adapter, suffix):
    return adapter(
        db_url=URL,
        session_table="sb_sessions_" + suffix,
        runs_table="sb_runs_" + suffix,
        sandbox_table="sb_bindings_" + suffix,
    )


async def dispose(db):
    if isinstance(db, AsyncPostgresDb):
        await db.db_engine.dispose()
    else:
        db.db_engine.dispose()


async def seed(store, run_id="run", session_id="session", attempt=None, created_at=1):
    def write(c):
        if c.execute(select(store.sessions).where(store.sessions.c.session_id == session_id)).first() is None:
            c.execute(
                store.sessions.insert().values(
                    session_id=session_id,
                    session_type="agent",
                    agent_id="agent",
                    user_id="user",
                    session_data={"trusted": "keep"},
                    created_at=created_at,
                )
            )
        c.execute(
            store.runs.insert().values(
                run_id=run_id,
                session_id=session_id,
                run_type="agent",
                agent_id="agent",
                user_id="user",
                status="RUNNING",
                created_at=1,
                run_data={
                    "run_id": run_id,
                    "session_id": session_id,
                    "agent_id": "agent",
                    "user_id": "user",
                    "status": "RUNNING",
                    "queue_attempt": attempt,
                    "input": {"input_content": "hello"},
                    "metadata": {"service": "keep"},
                },
            )
        )

    await store._transaction(write)


async def claim(store, **kwargs):
    return await store.aclaim(
        **{"agent_id": "agent", "session_id": "session", "user_id": "user", "run_id": "run", "owner": "owner", **kwargs}
    )


def computer(state):
    return SandboxHandle("ref", "name", "agent", "session", state.record["generation"], "running", "digest")


def result(lease):
    return {
        "type": "execution_finished",
        "run": {
            "run_id": lease.run_id,
            "session_id": lease.session_id,
            "agent_id": lease.agent_id,
            "user_id": lease.user_id,
            "status": "COMPLETED",
            "content": "done",
        },
        "session": {
            "session_id": lease.session_id,
            "user_id": lease.user_id,
            "session_data": {"trusted": "replace", "native_id": "native"},
        },
    }


async def staged(store):
    await seed(store)
    state = await claim(store)
    await store.aset_computer(state.lease, computer(state))
    await store.astage_result(state.lease, result(state.lease))
    return state.lease


async def rows(store):
    return await store._transaction(
        lambda c: tuple(
            dict(c.execute(select(t)).mappings().one()) for t in (store.runs, store.sessions, store.bindings)
        )
    )


async def test_independent_instances_have_one_owner(store):
    await seed(store)
    other_db = new_db(type(store.db), store.db.session_table_name.removeprefix("sb_sessions_"))
    other = _SandboxStore(other_db)
    outcomes = await asyncio.gather(claim(store), claim(other, owner="other"), return_exceptions=True)
    assert sum(isinstance(x, SandboxSessionBusy) for x in outcomes) == 1
    winner = next(x for x in outcomes if not isinstance(x, Exception))
    again = await claim(store, owner=winner.lease.owner)
    assert again.lease == winner.lease
    assert again.record["execution_id"] == winner.record["execution_id"]
    await seed(store, run_id="second")
    with pytest.raises(SandboxSessionBusy):
        await claim(store, run_id="second")
    await seed(store, run_id="parallel", session_id="parallel")
    assert (await claim(store, run_id="parallel", session_id="parallel")).record["phase"] == "executing"
    await dispose(other_db)


@pytest.mark.parametrize("adapter", [PostgresDb, AsyncPostgresDb])
async def test_tables_are_created_on_first_use_by_racing_processes(adapter):
    suffix = uuid4().hex[:12]
    dbs = [new_db(adapter, suffix) for _ in range(4)]
    stores = [_SandboxStore(db) for db in dbs]
    try:
        await asyncio.gather(*(store._ensure_tables() for store in stores))
        await seed(stores[0])
        state = await claim(stores[1])
        assert (await stores[2].aget(state.lease)).lease == state.lease
    finally:
        await stores[0]._transaction(
            lambda c: [table.drop(c) for table in (stores[0].bindings, stores[0].runs, stores[0].sessions)]
        )
        for db in dbs:
            await dispose(db)


async def test_generation_survives_json_number_precision(store):
    await seed(store)
    state = await claim(store)
    # JavaScript readers round integers above 2**53, so two generations could compare equal.
    assert 0 < state.record["generation"] < 2**53


async def test_bindings_table_serves_one_session_table(store):
    await store._ensure_tables()
    # A second session table pointed at the same bindings table, whose foreign key names the first.
    other = type(store.db)(
        db_url=URL, session_table=store.db.session_table_name + "_other", sandbox_table=store.db.sandbox_table_name
    )
    second = _SandboxStore(other)
    try:
        with pytest.raises(SandboxError, match="session table"):
            await second._ensure_tables()
    finally:
        runs = await second._table("runs", other.runs_table_name)
        sessions = await second._table("sessions", other.session_table_name)
        await store._transaction(lambda c: [table.drop(c) for table in (runs, sessions)])
        await dispose(other)


async def test_wrong_owner_rolls_back_first_binding(store):
    await seed(store)
    with pytest.raises(SandboxLeaseLost):
        await claim(store, user_id="attacker")
    assert await store._transaction(lambda c: c.execute(select(store.bindings)).first()) is None
    state = await claim(store)
    with pytest.raises(SandboxLeaseLost):
        await store.aget(replace(state.lease, agent_id="wrong"))


async def test_expiry_takeover_preserves_execution_and_fences_old_owner(store):
    await seed(store)
    old = await claim(store)
    await store._transaction(
        lambda c: c.execute(update(store.bindings).values(expires_at=func.clock_timestamp() - timedelta(seconds=1)))
    )
    with pytest.raises(SandboxLeaseLost):
        await store.arenew(old.lease)
    new = await claim(store, owner="new")
    assert new.lease.epoch == old.lease.epoch + 1
    assert new.record == old.record
    with pytest.raises(SandboxLeaseLost):
        await store.aset_computer(old.lease, computer(old))
    with pytest.raises(SandboxLeaseLost):
        await store.abegin_stop(old.lease, status="CANCELLED", reason="late")


async def test_new_queue_attempt_fences_live_lease_and_preserves_finalization(store):
    await seed(store, attempt=1)
    old = await claim(store, queue_attempt=1)
    await store.aset_computer(old.lease, computer(old))
    await store.astage_result(old.lease, result(old.lease))
    await store._transaction(
        lambda c: c.execute(
            update(store.runs).values(run_data={**result(old.lease)["run"], "status": "RUNNING", "queue_attempt": 2})
        )
    )
    new = await claim(store, owner="new", queue_attempt=2)
    assert new.record["phase"] == "finalizing"
    assert new.record["execution_id"] == old.record["execution_id"]
    with pytest.raises(SandboxLeaseLost):
        await store.astage_checkpoint(old.lease, REF)
    await store.astage_checkpoint(new.lease, REF)
    await store.aconfirm_stopped(new.lease, "ref")
    assert (await store.acommit(new.lease))["queue_attempt"] == 2


async def test_staging_is_not_completion_and_commit_is_atomic(store):
    lease = await staged(store)
    run, session, binding = await rows(store)
    assert run["status"] == "RUNNING"
    assert "sandbox" not in session["session_data"]
    with pytest.raises(SandboxError, match="recovery bytes"):
        await store.acommit(lease)
    with pytest.raises(SandboxError, match="checkpoint"):
        await store.aconfirm_stopped(lease, "ref")
    await store.astage_checkpoint(lease, REF)
    with pytest.raises(SandboxError, match="cleanup"):
        await store.acommit(lease)
    await store.aconfirm_stopped(lease, "ref")
    await store.acommit(lease)
    run, session, binding = await rows(store)
    assert run["status"] == "COMPLETED"
    assert session["session_data"]["trusted"] == "keep"
    assert session["session_data"]["sandbox"]["native"]["native_id"] == "native"
    assert session["session_data"]["sandbox"]["checkpoint"] == binding["record"]["checkpoint"]
    assert binding["owner"] is None and binding["record"]["phase"] == "idle"
    with pytest.raises(SandboxRunFinished) as caught:
        await claim(store)
    assert caught.value.run == run["run_data"]  # lost commit acknowledgement


async def test_write_failure_rolls_back_run_and_checkpoint_publication(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    engine = store.db.db_engine.sync_engine if isinstance(store.db, AsyncPostgresDb) else store.db.db_engine

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE") and store.sessions.name in statement:
            raise RuntimeError("injected terminal persistence failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="injected"):
            await store.acommit(lease)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    run, session, binding = await rows(store)
    assert run["status"] == "RUNNING" and "sandbox" not in session["session_data"]
    assert binding["record"]["phase"] == "finalizing"
    assert (await store.acommit(lease))["status"] == "COMPLETED"


async def test_stale_previous_turn_cannot_overwrite_new_turn(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    await store.acommit(lease)
    await seed(store, run_id="second")
    new = await claim(store, run_id="second")
    assert new.record["stopped_ref"] is None
    with pytest.raises(SandboxLeaseLost):
        await store.acommit(lease)
    assert new.record["checkpoint"]["sha256"] == REF.sha256


async def test_recreated_session_starts_a_fresh_binding(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store._transaction(lambda c: c.execute(delete(store.sessions)))
    bindings = await store._transaction(lambda c: c.execute(select(store.bindings)).all())
    assert bindings == []
    with pytest.raises(SandboxLeaseLost):
        await claim(store)
    # Same session id, created_at, run id and owner: nothing but the binding row tells them apart.
    await seed(store)
    fresh = await claim(store)
    assert fresh.record["phase"] == "executing" and fresh.record["result"] is None
    assert fresh.record["checkpoint"] is None and fresh.record["staged_checkpoint"] is None
    with pytest.raises(SandboxLeaseLost):
        await store.aget(lease)
    with pytest.raises(SandboxLeaseLost):
        await store.abegin_stop(lease, status="CANCELLED", reason="stale coordinator")


async def test_cancelled_call_waits_for_its_sync_transaction(store):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("AsyncPostgresDb runs the transaction on the event loop and rolls it back on cancellation")
    finished = []

    def slow(connection):
        time.sleep(0.5)
        finished.append(True)

    await store._ensure_tables()
    task = asyncio.create_task(store._transaction(slow))
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished


async def test_shutdown_intent_is_durable_and_requires_cleanup(store):
    await seed(store)
    state = await claim(store)
    await store.aset_computer(state.lease, computer(state))
    with pytest.raises(SandboxError, match="intent"):
        await store.aconfirm_stopped(state.lease, "ref")
    await store.abegin_stop(state.lease, status="CANCELLED", reason="requested")
    with pytest.raises(SandboxError, match="cleanup"):
        await store.afinish_stop(state.lease)
    with pytest.raises(SandboxError):
        await store.astage_result(state.lease, result(state.lease))
    await store.aconfirm_stopped(state.lease, "ref")
    assert (await store.afinish_stop(state.lease))["status"] == "CANCELLED"
    _, session, binding = await rows(store)
    assert "sandbox" not in session["session_data"] and binding["record"]["checkpoint"] is None


async def test_external_cancellation_wins_over_staged_success(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    await store._transaction(
        lambda c: c.execute(
            update(store.runs).values(status="CANCELLED", run_data={**result(lease)["run"], "status": "CANCELLED"})
        )
    )
    with pytest.raises(SandboxRunFinished) as caught:
        await store.acommit(lease)
    assert caught.value.run["status"] == "CANCELLED"
    # Cleanup was already confirmed, so the commit itself released the session.
    run, _, binding = await rows(store)
    assert run["status"] == "CANCELLED" and binding["record"]["phase"] == "idle" and binding["owner"] is None
    assert binding["record"]["checkpoint"] is None
    with pytest.raises(SandboxRunFinished):
        await claim(store)


async def test_commit_after_external_completion_releases_the_session(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    await finish_elsewhere(store, "COMPLETED")
    with pytest.raises(SandboxRunFinished) as caught:
        await store.acommit(lease)
    # The stored completion stands, and the staged checkpoint is not promoted.
    assert caught.value.run["content"] == "finished elsewhere"
    binding = (await rows(store))[2]
    assert binding["record"]["phase"] == "idle" and binding["record"]["checkpoint"] is None
    await seed(store, run_id="second")
    assert (await claim(store, run_id="second")).record["phase"] == "executing"


async def test_staged_result_is_immutable_and_identity_bound(store):
    lease = await staged(store)
    changed = result(lease)
    changed["session"]["session_data"]["native_id"] = "other"
    with pytest.raises(SandboxError, match="immutable"):
        await store.astage_result(lease, changed)
    with pytest.raises(SandboxError, match="identity"):
        await store.astage_result(lease, result(replace(lease, user_id="other")))


async def test_core_session_upsert_does_not_strand_active_lease(store):
    await seed(store)
    # AgentOS PATCH /sessions reads the session, edits it, and upserts the whole session_data blob.
    stale = AgentSession(
        session_id="session", agent_id="agent", user_id="user", session_data={"session_name": "x"}, created_at=1
    )
    state = await claim(store)
    if isinstance(store.db, AsyncPostgresDb):
        await store.db.upsert_session(stale)
    else:
        await asyncio.to_thread(store.db.upsert_session, stale)
    await store.aset_computer(state.lease, computer(state))
    await store.astage_result(state.lease, result(state.lease))
    await store.astage_checkpoint(state.lease, REF)
    await store.aconfirm_stopped(state.lease, "ref")
    assert (await store.acommit(state.lease))["status"] == "COMPLETED"


async def test_runtime_result_cannot_rewrite_service_fields(store):
    await seed(store)
    state = await claim(store)
    await store.aset_computer(state.lease, computer(state))
    forged = result(state.lease)
    forged["run"].update(
        input={"input_content": "forged"},
        created_at=0,
        parent_run_id="other",
        session_state={"admin": True},
        metadata={"native": "value", "service": "forged"},
    )
    await store.astage_result(state.lease, forged)
    await store.astage_checkpoint(state.lease, REF)
    await store.aconfirm_stopped(state.lease, "ref")
    run = await store.acommit(state.lease)
    assert run["content"] == "done" and run["status"] == "COMPLETED"
    assert run["input"] == {"input_content": "hello"}
    assert "created_at" not in run and "parent_run_id" not in run and "session_state" not in run
    assert run["metadata"]["service"] == "keep"
    assert run["metadata"]["sandbox"]["native_metadata"] == {"native": "value", "service": "forged"}


async def test_cancelled_result_keeps_its_cancellation_stage(store):
    await seed(store)
    state = await claim(store)
    await store.aset_computer(state.lease, computer(state))
    cancelled = result(state.lease)
    cancelled["run"].update(status="CANCELLED", cancellation_stage="tool_call")
    await store.astage_result(state.lease, cancelled)
    await store.astage_checkpoint(state.lease, REF)
    await store.aconfirm_stopped(state.lease, "ref")
    run = await store.acommit(state.lease)
    assert run["status"] == "CANCELLED" and run["cancellation_stage"] == "tool_call"


async def test_stop_keeps_existing_content_and_staged_output(store):
    lease = await staged(store)
    run_data = (await rows(store))[0]["run_data"]
    await store._transaction(
        lambda c: c.execute(update(store.runs).values(run_data={**run_data, "content": "partial"}))
    )
    await store.abegin_stop(lease, status="CANCELLED", reason="Cancelled by the user")
    await store.aconfirm_stopped(lease, "ref")
    run = await store.afinish_stop(lease)
    assert run["status"] == "CANCELLED" and run["content"] == "partial"
    assert run["metadata"]["sandbox"]["runtime_content"] == "done"
    assert run["metadata"]["service"] == "keep"


async def test_sync_api_contract(store):
    if isinstance(store.db, AsyncPostgresDb):
        with pytest.raises(TypeError, match="async"):
            store.claim(agent_id="agent", session_id="session", user_id="user", run_id="run", owner="owner")
    else:
        await seed(store)
        state = await asyncio.to_thread(
            store.claim, agent_id="agent", session_id="session", user_id="user", run_id="run", owner="owner"
        )
        assert (await asyncio.to_thread(store.get, state.lease)).lease == state.lease
        await asyncio.to_thread(store.begin_stop, state.lease, status="ERROR", reason="no compute")
        stopped = await asyncio.to_thread(store.finish_stop, state.lease)
        assert stopped["status"] == "ERROR" and stopped["content"] == "no compute"


async def finish_elsewhere(store, status, content="finished elsewhere"):
    run_data = (await rows(store))[0]["run_data"]
    await store._transaction(
        lambda c: c.execute(
            update(store.runs).values(status=status, run_data={**run_data, "status": status, "content": content})
        )
    )


async def test_stop_after_external_completion_releases_the_session(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await finish_elsewhere(store, "COMPLETED")
    await store.abegin_stop(lease, status="ERROR", reason="Service run was finished elsewhere")
    await store.aconfirm_stopped(lease, "ref")
    run = await store.afinish_stop(lease)
    # The stored completion stands; the staged checkpoint is not promoted, since nothing ties it to that result.
    assert run["status"] == "COMPLETED" and run["content"] == "finished elsewhere"
    binding = (await rows(store))[2]
    assert binding["record"]["phase"] == "idle" and binding["record"]["checkpoint"] is None
    await seed(store, run_id="second")
    assert (await claim(store, run_id="second")).record["phase"] == "executing"


async def test_regenerated_run_counts_as_finished(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    await finish_elsewhere(store, "REGENERATED")
    with pytest.raises(SandboxRunFinished):
        await store.acommit(lease)
    assert (await rows(store))[0]["status"] == "REGENERATED"


async def test_regenerated_run_is_not_reopened(store):
    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    await store.acommit(lease)
    await finish_elsewhere(store, "REGENERATED")
    with pytest.raises(SandboxRunFinished):
        await claim(store)


async def test_repeated_cancellation_still_waits_for_its_sync_transaction(store):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("AsyncPostgresDb runs the transaction on the event loop and rolls it back on cancellation")
    finished = []

    def slow(connection):
        time.sleep(0.6)
        finished.append(True)

    await store._ensure_tables()
    task = asyncio.create_task(store._transaction(slow))
    await asyncio.sleep(0.1)
    task.cancel()
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished


async def test_deleting_a_run_under_an_active_turn_is_refused(store):
    lease = await staged(store)
    delete = store.db.delete_run
    with pytest.raises(Exception):
        if isinstance(store.db, AsyncPostgresDb):
            await delete("run")
        else:
            await asyncio.to_thread(delete, "run")
    run, _, binding = await rows(store)
    assert run["run_id"] == "run" and binding["run_id"] == "run"
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    await store.acommit(lease)
    # Once the turn is committed the binding no longer holds the run.
    if isinstance(store.db, AsyncPostgresDb):
        assert await delete("run")
    else:
        assert await asyncio.to_thread(delete, "run")


async def test_cancelled_first_use_waits_for_table_setup(store, monkeypatch):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("AsyncPostgresDb resolves tables on the event loop")
    finished = []
    get_table = store.db._get_table

    def slow(*args, **kwargs):
        time.sleep(0.5)
        table = get_table(*args, **kwargs)
        finished.append(True)
        return table

    monkeypatch.setattr(store.db, "_get_table", slow)
    task = asyncio.create_task(store._ensure_tables())
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished


async def test_session_deletion_waits_for_a_sandbox_operation(store, monkeypatch):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("Interleaves a blocking database call with the store's worker thread")
    await seed(store)
    state = await claim(store)
    service_run = store._service_run
    holding = threading.Event()

    def pause_after_binding(*args, **kwargs):
        # The binding is locked; give a session deletion time to issue its DELETE before the run is.
        holding.set()
        time.sleep(2)
        return service_run(*args, **kwargs)

    monkeypatch.setattr(store, "_service_run", pause_after_binding)
    operation = asyncio.create_task(store.aget(state.lease))
    await asyncio.to_thread(holding.wait, 5)
    deleted = await asyncio.to_thread(store.db.delete_session, "session")
    assert (await operation).lease == state.lease
    assert deleted


async def test_run_deletion_racing_a_sandbox_operation_is_refused_not_deadlocked(store, monkeypatch):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("Interleaves a blocking database call with the store's worker thread")
    await seed(store)
    state = await claim(store)
    service_run = store._service_run
    holding = threading.Event()

    def pause(*args, **kwargs):
        # The store's first locks are held; give the run deletion time to issue its DELETE.
        holding.set()
        time.sleep(2)
        return service_run(*args, **kwargs)

    monkeypatch.setattr(store, "_service_run", pause)
    operation = asyncio.create_task(store.aget(state.lease))
    await asyncio.to_thread(holding.wait, 5)
    with pytest.raises(Exception) as caught:
        await asyncio.to_thread(store.db.delete_run, "run")
    assert "foreign key" in str(caught.value).lower() and "deadlock" not in str(caught.value).lower()
    assert (await operation).lease == state.lease


async def test_bindings_table_in_another_schema_is_refused(store):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("Schema setup uses the sync engine")
    other_schema = "sbx_" + uuid4().hex[:8]
    other = PostgresDb(
        db_url=URL,
        db_schema=other_schema,
        session_table=store.db.session_table_name,
        runs_table=store.db.runs_table_name,
        sandbox_table=store.db.sandbox_table_name,
    )
    await _SandboxStore(other)._ensure_tables()
    await store._table("sessions", store.db.session_table_name)
    await store._table("runs", store.db.runs_table_name)
    # A same-named bindings table in this schema whose keys point at the other schema's tables.
    b, s, r, home = (
        store.db.sandbox_table_name,
        store.db.session_table_name,
        store.db.runs_table_name,
        store.db.db_schema,
    )
    with store.db.db_engine.begin() as connection:
        connection.execute(text(f'CREATE TABLE "{home}"."{b}" (LIKE "{other_schema}"."{b}" INCLUDING DEFAULTS)'))
        connection.execute(text(f'ALTER TABLE "{home}"."{b}" ADD PRIMARY KEY (namespace, session_id)'))
        connection.execute(
            text(
                f'ALTER TABLE "{home}"."{b}" ADD FOREIGN KEY (session_id) REFERENCES "{other_schema}"."{s}" (session_id)'
            )
        )
        connection.execute(
            text(f'ALTER TABLE "{home}"."{b}" ADD FOREIGN KEY (run_id) REFERENCES "{other_schema}"."{r}" (run_id)')
        )
    try:
        with pytest.raises(SandboxError, match="session table"):
            await store._ensure_tables()
    finally:
        with store.db.db_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{other_schema}" CASCADE'))
            connection.execute(text(f'DROP TABLE "{home}"."{b}"'))
        # The fixture's teardown recreates a correct bindings table and drops it.
        store.db._invalidate_table_cache(b)
        other.db_engine.dispose()


async def test_bindings_table_without_its_key_is_refused(store):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("Table setup uses the sync engine")
    sessions = await store._table("sessions", store.db.session_table_name)
    runs = await store._table("runs", store.db.runs_table_name)
    b, home = store.db.sandbox_table_name, store.db.db_schema
    # Right columns and foreign keys, but nothing that makes (namespace, session_id) unique.
    with store.db.db_engine.begin() as connection:
        connection.execute(
            text(
                f'CREATE TABLE "{home}"."{b}" (namespace varchar NOT NULL, session_id varchar NOT NULL '
                f'REFERENCES "{home}"."{sessions.name}" (session_id) ON DELETE CASCADE, agent_id varchar NOT NULL, '
                f'user_id varchar, epoch bigint NOT NULL, owner varchar, run_id varchar REFERENCES "{home}"."{runs.name}" '
                "(run_id), queue_attempt bigint, expires_at timestamptz, record jsonb NOT NULL)"
            )
        )
    try:
        with pytest.raises(SandboxError, match="key"):
            await store._ensure_tables()
    finally:
        with store.db.db_engine.begin() as connection:
            connection.execute(text(f'DROP TABLE "{home}"."{b}"'))
        store.db._invalidate_table_cache(b)


async def test_store_operation_does_not_wait_for_an_ordinary_session_update(store):
    await seed(store)
    state = await claim(store)
    engine = create_engine(URL)
    writer = await asyncio.to_thread(engine.connect)
    transaction = await asyncio.to_thread(writer.begin)
    # An ordinary non-key session write, held open; KEY SHARE must not conflict with it.
    await asyncio.to_thread(
        lambda: writer.execute(
            store.sessions.update().where(store.sessions.c.session_id == "session").values(updated_at=2)
        )
    )
    try:
        operation = asyncio.create_task(store.aget(state.lease))
        await asyncio.sleep(1)
        finished_while_held = operation.done()
    finally:
        await asyncio.to_thread(transaction.commit)
        await asyncio.to_thread(writer.close)
        engine.dispose()
    assert (await operation).lease == state.lease
    assert finished_while_held


async def test_bindings_table_cascading_run_deletes_is_refused(store):
    if isinstance(store.db, AsyncPostgresDb):
        pytest.skip("Table setup uses the sync engine")
    sessions = await store._table("sessions", store.db.session_table_name)
    runs = await store._table("runs", store.db.runs_table_name)
    b, home = store.db.sandbox_table_name, store.db.db_schema
    # Correct key and targets, but deleting a run would silently remove the binding of its active turn.
    with store.db.db_engine.begin() as connection:
        connection.execute(
            text(
                f'CREATE TABLE "{home}"."{b}" (namespace varchar NOT NULL, session_id varchar NOT NULL '
                f'REFERENCES "{home}"."{sessions.name}" (session_id) ON DELETE CASCADE, agent_id varchar NOT NULL, '
                f'user_id varchar, epoch bigint NOT NULL, owner varchar, run_id varchar REFERENCES "{home}"."{runs.name}" '
                "(run_id) ON DELETE CASCADE, queue_attempt bigint, expires_at timestamptz, record jsonb NOT NULL, "
                "PRIMARY KEY (namespace, session_id))"
            )
        )
    try:
        with pytest.raises(SandboxError, match="cascade"):
            await store._ensure_tables()
    finally:
        with store.db.db_engine.begin() as connection:
            connection.execute(text(f'DROP TABLE "{home}"."{b}"'))
        store.db._invalidate_table_cache(b)
