"""Real PostgreSQL fencing and atomic recovery publication; no model calls."""

import asyncio
import os
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, event, func, select, update

from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.sandbox.base import SandboxError, SandboxHandle
from agno.sandbox.checkpoint import CheckpointRef
from agno.sandbox.postgres import (
    PostgresSandboxStore,
    SandboxLeaseLost,
    SandboxRunFinished,
    SandboxSessionBusy,
)

URL = os.environ.get("AGNO_TEST_SANDBOX_DB_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="Set AGNO_TEST_SANDBOX_DB_URL")]
REF = CheckpointRef("a" * 64, 10240)


@pytest_asyncio.fixture(params=[PostgresDb, AsyncPostgresDb])
async def store(request):
    suffix = uuid4().hex[:12]
    db = request.param(db_url=URL, session_table="sb_sessions_" + suffix, runs_table="sb_runs_" + suffix)
    store = PostgresSandboxStore(db, table_name="sb_bindings_" + suffix)
    await store.asetup()
    yield store
    await store._transaction(lambda c: [table.drop(c) for table in (store.bindings, store.runs, store.sessions)])
    if isinstance(db, AsyncPostgresDb):
        await db.db_engine.dispose()
    else:
        db.db_engine.dispose()


async def seed(store, run_id="run", session_id="session", attempt=None):
    def write(c):
        if c.execute(select(store.sessions).where(store.sessions.c.session_id == session_id)).first() is None:
            c.execute(
                store.sessions.insert().values(
                    session_id=session_id,
                    session_type="agent",
                    agent_id="agent",
                    user_id="user",
                    session_data={"trusted": "keep"},
                    created_at=1,
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
    other = PostgresSandboxStore(store.db, table_name=store.bindings.name)
    await other.asetup()
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


async def test_deleted_and_recreated_session_cannot_inherit_old_compute(store):
    await seed(store)
    await claim(store)
    await store._transaction(lambda c: c.execute(delete(store.sessions)))
    await seed(store)
    with pytest.raises(SandboxLeaseLost, match="replaced"):
        await claim(store)


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
    with pytest.raises(SandboxRunFinished):
        await store.acommit(lease)
    # Recovery may take over a terminal service run solely to finish cleanup.
    state = await claim(store)
    await store.abegin_stop(state.lease, status="ERROR", reason="must preserve cancellation")
    assert (await store.afinish_stop(state.lease))["status"] == "CANCELLED"
    assert (await rows(store))[2]["record"]["checkpoint"] is None


async def test_native_data_cannot_replace_session_incarnation(store):
    lease = await staged(store)
    changed = result(lease)
    changed["session"]["session_data"]["_sandbox_incarnation"] = "evil"
    with pytest.raises(SandboxError, match="immutable"):
        await store.astage_result(lease, changed)
    with pytest.raises(SandboxError, match="identity"):
        await store.astage_result(lease, result(replace(lease, user_id="other")))


async def test_sync_api_contract(store):
    if isinstance(store.db, AsyncPostgresDb):
        with pytest.raises(TypeError, match="async"):
            store.setup()
    else:
        await seed(store)
        state = await asyncio.to_thread(
            store.claim, agent_id="agent", session_id="session", user_id="user", run_id="run", owner="owner"
        )
        assert (await asyncio.to_thread(store.get, state.lease)).lease == state.lease
        await asyncio.to_thread(store.begin_stop, state.lease, status="ERROR", reason="no compute")
        assert (await asyncio.to_thread(store.finish_stop, state.lease))["status"] == "ERROR"


async def test_atomic_admission_does_not_leave_a_rejected_run(store):
    await seed(store)
    await claim(store)
    value = {
        **result((await claim(store)).lease)["run"],
        "run_id": "rejected",
        "status": "RUNNING",
        "input": {"input_content": "new"},
    }
    with pytest.raises(SandboxSessionBusy):
        await claim(store, run_id="rejected", prepared_run=value)
    assert await store._transaction(lambda c: c.execute(select(store.runs.c.run_id)).scalars().all()) == ["run"]


async def test_existing_non_sandbox_history_requires_explicit_migration(store):
    await seed(store)
    await store._transaction(lambda c: c.execute(update(store.runs).values(status="COMPLETED")))
    value = {"run_id": "new", "session_id": "session", "agent_id": "agent", "user_id": "user", "status": "RUNNING"}
    with pytest.raises(SandboxError, match="migrate explicitly"):
        await claim(store, run_id="new", prepared_run=value)
    assert await store._transaction(lambda c: c.execute(select(store.bindings)).first()) is None
    assert await store._transaction(lambda c: c.execute(select(store.runs.c.run_id)).scalars().all()) == ["run"]


async def test_cancelled_provider_operation_drains_before_releasing_ownership_rows(store):
    await seed(store)
    state = await claim(store)
    entered, release = asyncio.Event(), asyncio.Event()

    async def operation(record):
        entered.set()
        await release.wait()
        record["drained"] = True
        return record

    active = asyncio.create_task(store._aoperation(state.lease, operation))
    await entered.wait()
    active.cancel()
    contender = asyncio.create_task(claim(store, owner="other"))
    await asyncio.sleep(0.05)
    assert not active.done() and not contender.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await active
    with pytest.raises(SandboxSessionBusy):
        await contender
    assert (await store.aget(state.lease)).record["drained"] is True


async def test_compute_cannot_replace_service_input_or_metadata(store):
    await seed(store)
    initial = await store._transaction(lambda c: dict(c.execute(select(store.runs.c.run_data)).scalar_one()))
    initial.update(input={"input_content": "original"}, metadata={"tenant": "trusted"})
    await store._transaction(lambda c: c.execute(update(store.runs).values(run_data=initial)))
    state = await claim(store)
    await store.aset_computer(state.lease, computer(state))
    output = result(state.lease)
    output["run"].update(input={"input_content": "forged"}, metadata={"tenant": "forged", "warnings": []})
    await store.astage_result(state.lease, output)
    await store.astage_checkpoint(state.lease, REF)
    await store.aconfirm_stopped(state.lease, "ref")
    committed = await store.acommit(state.lease)
    assert committed["input"] == {"input_content": "original"}
    assert committed["metadata"]["tenant"] == "trusted"
    assert committed["metadata"]["sandbox"]["native_metadata"]["tenant"] == "forged"


async def test_pending_prepare_after_claim_keeps_attempt_and_binding(store):
    from agno.run.agent import RunInput, RunOutput
    from agno.run.base import RunStatus

    pending = RunOutput(
        run_id="run",
        session_id="session",
        agent_id="agent",
        user_id="user",
        input=RunInput(input_content="input"),
        status=RunStatus.pending,
    ).to_dict()
    await store.aprepare(pending)
    await store._transaction(
        lambda c: c.execute(
            update(store.runs).values(run_data={**pending, "status": "RUNNING", "queue_attempt": 2}, status="RUNNING")
        )
    )
    state = await claim(store, queue_attempt=2)
    await store.aprepare(pending)
    assert (await store.aget(state.lease)).record["phase"] == "executing"
    assert (await rows(store))[0]["run_data"]["queue_attempt"] == 2


async def test_never_started_cancel_allows_next_turn(store):
    from agno.run.agent import RunInput, RunOutput
    from agno.run.base import RunStatus
    from agno.run.status_persist import RunPersistOutcome

    pending = RunOutput(
        run_id="run",
        session_id="session",
        agent_id="agent",
        user_id="user",
        input=RunInput(input_content="input"),
        status=RunStatus.pending,
    ).to_dict()
    await store.aprepare(pending)
    outcome = await store._aclaim_stop(
        agent_id="agent",
        session_id="session",
        user_id="user",
        run_id="run",
        queue_attempt=0,
        status="CANCELLED",
        reason="cancelled",
    )
    assert outcome == RunPersistOutcome.UPDATED
    await seed(store, run_id="next")
    assert (await claim(store, run_id="next")).record["phase"] == "executing"


async def test_stale_event_writer_cannot_rewrite_new_attempt(store):
    from copy import deepcopy

    lease = await staged(store)
    await store.astage_checkpoint(lease, REF)
    await store.aconfirm_stopped(lease, "ref")
    run = await store.acommit(lease)
    events = [{"event": "RunCompleted", "event_index": 3, "run_id": "run"}]
    await store._apublish_events(run, events)
    stale = deepcopy(run)
    stale["metadata"]["sandbox"]["epoch"] -= 1
    with pytest.raises(SandboxLeaseLost):
        await store._apublish_events(stale, [{"event": "RunCompleted", "event_index": 4}])
    assert (await rows(store))[0]["run_data"]["events"] == events


async def test_queue_termination_fences_owner_and_rejects_stale_attempt(store):
    from agno.run.status_persist import RunPersistOutcome

    await seed(store, attempt=2)
    old = await claim(store, queue_attempt=2)
    stale = await store._aclaim_stop(
        agent_id="agent",
        session_id="session",
        user_id="user",
        run_id="run",
        queue_attempt=1,
        status="ERROR",
        reason="stale",
    )
    assert stale == RunPersistOutcome.STALE_ATTEMPT
    assert (await store.aget(old.lease)).record["phase"] == "executing"
    stopping = await store._aclaim_stop(
        agent_id="agent",
        session_id="session",
        user_id="user",
        run_id="run",
        queue_attempt=2,
        status="CANCELLED",
        reason="cancelled",
    )
    assert stopping.record["phase"] == "stopping"
    with pytest.raises(SandboxLeaseLost):
        await store.aget(old.lease)
    assert (await store.afinish_stop(stopping.lease))["status"] == "CANCELLED"


@pytest.mark.parametrize("first_status,next_status", [("CANCELLED", "ERROR"), ("ERROR", "CANCELLED")])
async def test_stop_takeover_preserves_cancellation_over_error(store, first_status, next_status):
    await seed(store, attempt=1)
    await claim(store, queue_attempt=1)
    args = dict(agent_id="agent", session_id="session", user_id="user", run_id="run", queue_attempt=1)
    first = await store._aclaim_stop(**args, status=first_status, reason="first durable intent")
    second = await store._aclaim_stop(**args, status=next_status, reason="competing cleanup")
    assert second.record["stop_status"] == "CANCELLED"
    assert second.record["stop_reason"] == (
        "first durable intent" if first_status == "CANCELLED" else "competing cleanup"
    )
    with pytest.raises(SandboxLeaseLost):
        await store.aget(first.lease)
    assert (await store.afinish_stop(second.lease))["status"] == "CANCELLED"
