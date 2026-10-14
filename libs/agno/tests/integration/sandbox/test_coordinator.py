"""Full Docker + Postgres recovery boundary, using a credential-free runtime."""

import asyncio
import os
from dataclasses import dataclass, field, replace
from typing import Dict
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from agno.sandbox import SandboxError
from agno.sandbox.checkpoint import CheckpointRef, FileCheckpointStore
from agno.sandbox.coordinator import SandboxCoordinator
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.postgres import SandboxSessionBusy
from agno.sandbox.transfer import DockerCheckpointTransfer

URL, IMAGE = os.environ.get("AGNO_TEST_SANDBOX_DB_URL"), os.environ.get("AGNO_TEST_RUNTIME_IMAGE")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not URL or not IMAGE, reason="Enable real Postgres and runtime image"),
]


@dataclass(frozen=True)
class Target:
    agent_id: str
    session_id: str
    env: Dict[str, str] = field(default_factory=dict)


@pytest_asyncio.fixture(params=[PostgresDb, AsyncPostgresDb])
async def system(request, tmp_path):
    suffix = uuid4().hex[:12]
    db = request.param(
        db_url=URL,
        session_table="co_sessions_" + suffix,
        runs_table="co_runs_" + suffix,
        sandbox_table="co_bindings_" + suffix,
    )
    provider = DockerSandbox(IMAGE, namespace="coordinator-" + suffix, memory_mb=512, workspace_mb=32)
    transfer = DockerCheckpointTransfer(provider, FileCheckpointStore(tmp_path / "objects"))
    coordinator = SandboxCoordinator(db, provider, transfer, poll_interval=0.05)
    spec = Target("agent", "session", env={"AGNO_SANDBOX_TEST_RUNTIME": "1"})
    handles = []
    original = provider.acreate

    async def create(session_id, **kwargs):
        handle = await original(session_id, **kwargs)
        handles.append(handle)
        return handle

    provider.acreate = create
    yield coordinator, spec, tmp_path
    for handle in handles:
        await provider.adestroy(handle)
    store = coordinator.store
    await store._transaction(lambda c: [t.drop(c) for t in (store.bindings, store.runs, store.sessions)])
    if isinstance(db, AsyncPostgresDb):
        await db.db_engine.dispose()
    else:
        db.db_engine.dispose()


async def run(coordinator, spec, run_id="first", **kwargs):
    return await coordinator.arun(
        spec.session_id,
        agent_id=spec.agent_id,
        env=spec.env,
        run_id=run_id,
        input=run_id,
        sdk="fixture",
        user_id="user",
        **kwargs,
    )


async def binding(coordinator):
    return await coordinator.store._transaction(
        lambda c: dict(c.execute(select(coordinator.store.bindings)).mappings().one())
    )


async def recovered_effects(coordinator, tmp_path):
    record = (await binding(coordinator))["record"]
    target = tmp_path / uuid4().hex
    state = await coordinator.transfer.store.arestore(CheckpointRef(**record["checkpoint"]), target)
    assert state["binding"] == record["checkpoint_identity"]
    return (target / "workspace/fixture-effects.txt").read_text().splitlines()


async def test_two_turns_replace_compute_and_restore_files_with_conversation(system):
    coordinator, spec, root = system
    first = await run(coordinator, spec)
    assert first.status == RunStatus.completed
    previous = (await binding(coordinator))["record"]
    assert previous["computer"] is None and previous["phase"] == "idle"
    second = await run(coordinator, spec, "second")
    assert second.status == RunStatus.completed
    assert await recovered_effects(coordinator, root) == ["first", "second"]
    assert (await binding(coordinator))["record"]["generation"] > previous["generation"]
    again = await run(coordinator, spec, "second")
    assert again.to_dict() == second.to_dict()


async def test_checkpoint_failure_retries_finalization_without_repeating_tools(system, monkeypatch):
    coordinator, spec, root = system
    capture = coordinator.transfer.acapture

    async def unavailable(*args, **kwargs):
        raise OSError("checkpoint store unavailable")

    monkeypatch.setattr(coordinator.transfer, "acapture", unavailable)
    with pytest.raises(OSError, match="unavailable"):
        await run(coordinator, spec)
    record = (await binding(coordinator))["record"]
    assert record["phase"] == "finalizing" and record["result"]["run"]["status"] == "COMPLETED"
    monkeypatch.setattr(coordinator.transfer, "acapture", capture)
    fresh = SandboxCoordinator(coordinator.store.db, coordinator.provider, coordinator.transfer, poll_interval=0.05)
    assert (await run(fresh, spec)).status == RunStatus.completed
    assert await recovered_effects(coordinator, root) == ["first"]


async def test_lost_start_ack_reconnects_to_same_execution(system, monkeypatch):
    coordinator, spec, root = system
    start = coordinator.client.astart

    async def lost_ack(*args, **kwargs):
        await start(*args, **kwargs)
        raise SandboxError("lost start acknowledgement")

    monkeypatch.setattr(coordinator.client, "astart", lost_ack)
    with pytest.raises(SandboxError, match="lost start"):
        await run(coordinator, spec)
    monkeypatch.setattr(coordinator.client, "astart", start)
    assert (await run(coordinator, spec)).status == RunStatus.completed
    assert await recovered_effects(coordinator, root) == ["first"]


async def test_lost_commit_ack_returns_stored_output_without_compute(system, monkeypatch):
    coordinator, spec, root = system
    commit = coordinator.store.acommit

    async def lost_ack(*args, **kwargs):
        await commit(*args, **kwargs)
        raise OSError("lost commit acknowledgement")

    monkeypatch.setattr(coordinator.store, "acommit", lost_ack)
    with pytest.raises(OSError, match="lost commit"):
        await run(coordinator, spec)
    monkeypatch.setattr(coordinator.store, "acommit", commit)
    assert (await run(coordinator, spec)).status == RunStatus.completed
    assert await recovered_effects(coordinator, root) == ["first"]


async def test_terminal_event_follows_atomic_database_commit(system):
    coordinator, spec, _ = system
    terminal_seen = False
    async for value in coordinator._astream(
        spec.session_id,
        agent_id=spec.agent_id,
        env=spec.env,
        run_id="first",
        input="first",
        sdk="fixture",
        user_id="user",
    ):
        if not isinstance(value, RunOutput) and value.event == "RunCompleted":
            terminal_seen = True
            state = await binding(coordinator)
            assert state["record"]["phase"] == "idle" and state["record"]["checkpoint"]
            row = await coordinator.store._transaction(
                lambda c: c.execute(select(coordinator.store.runs)).mappings().one()
            )
            assert row["status"] == "COMPLETED"
    assert terminal_seen


async def test_same_session_contention_and_independent_sessions(system):
    coordinator, spec, _ = system
    capture = coordinator.transfer.acapture
    entered, release = asyncio.Event(), asyncio.Event()

    async def pause_capture(*args, **kwargs):
        entered.set()
        await release.wait()
        return await capture(*args, **kwargs)

    coordinator.transfer.acapture = pause_capture
    first = asyncio.create_task(run(coordinator, spec))
    await asyncio.wait_for(entered.wait(), 20)
    second = asyncio.create_task(run(coordinator, spec, "second"))
    # Capture holds the database operation fence; admission must wait for it.
    await asyncio.sleep(0.1)
    assert not second.done()
    release.set()
    outcomes = await asyncio.gather(first, second, return_exceptions=True)
    assert outcomes[0].status == RunStatus.completed
    if isinstance(outcomes[1], SandboxSessionBusy):
        assert (await run(coordinator, spec, "second")).status == RunStatus.completed
    else:
        assert outcomes[1].status == RunStatus.completed
    other = replace(spec, session_id="independent")
    assert (await run(coordinator, other, "independent")).status == RunStatus.completed


async def test_lost_destroy_ack_finalizes_without_restore_or_execution(system, monkeypatch):
    coordinator, spec, root = system
    destroy = coordinator.provider.adestroy

    async def lost_ack(handle):
        await destroy(handle)
        raise OSError("lost destroy acknowledgement")

    monkeypatch.setattr(coordinator.provider, "adestroy", lost_ack)
    with pytest.raises(OSError, match="lost destroy"):
        await run(coordinator, spec)
    assert (await binding(coordinator))["record"]["staged_checkpoint"]
    monkeypatch.setattr(coordinator.provider, "adestroy", destroy)
    assert (await run(coordinator, spec)).status == RunStatus.completed
    assert await recovered_effects(coordinator, root) == ["first"]


async def test_lost_compute_before_checkpoint_fails_without_model_replay(system, monkeypatch):
    coordinator, spec, _ = system
    capture = coordinator.transfer.acapture

    async def lose_computer(handle, **kwargs):
        await coordinator.provider.adestroy(handle)
        raise OSError("host lost before checkpoint")

    monkeypatch.setattr(coordinator.transfer, "acapture", lose_computer)
    with pytest.raises(OSError, match="host lost"):
        await run(coordinator, spec)
    monkeypatch.setattr(coordinator.transfer, "acapture", capture)
    output = await run(coordinator, spec)
    assert output.status == RunStatus.error and "will not be repeated" in output.content
    assert output.metadata["retryable"] is False
    assert (await binding(coordinator))["record"]["checkpoint"] is None


async def test_restore_manifest_mismatch_is_rejected_before_execution(system, monkeypatch):
    coordinator, spec, root = system
    await run(coordinator, spec)
    restore = coordinator.transfer.arestore

    async def wrong_identity(*args, **kwargs):
        state = await restore(*args, **kwargs)
        state["binding"]["session_id"] = "other"
        return state

    monkeypatch.setattr(coordinator.transfer, "arestore", wrong_identity)
    with pytest.raises(SandboxError, match="manifest"):
        await run(coordinator, spec, "second")
    assert await recovered_effects(coordinator, root) == ["first"]
    monkeypatch.setattr(coordinator.transfer, "arestore", restore)
    assert (await run(coordinator, spec, "second")).status == RunStatus.completed
    assert await recovered_effects(coordinator, root) == ["first", "second"]


async def test_cancellation_discards_current_files_and_keeps_previous_boundary(system, monkeypatch):
    from agno.run import cancel

    coordinator, spec, root = system
    await run(coordinator, spec)

    async def cancelled(run_id):
        return run_id == "second"

    monkeypatch.setattr(cancel, "ais_cancelled", cancelled)

    async def must_not_allocate(*args, **kwargs):
        pytest.fail("Cancelled turn allocated compute")

    monkeypatch.setattr(coordinator.provider, "acreate", must_not_allocate)
    result = await run(coordinator, spec, "second", config={"delay": 2})
    assert result.status == RunStatus.cancelled
    assert await recovered_effects(coordinator, root) == ["first"]
    assert (await binding(coordinator))["record"]["phase"] == "idle"


async def test_changed_input_and_configuration_cannot_reuse_active_execution(system, monkeypatch):
    coordinator, spec, _ = system
    start = coordinator.client.astart

    async def lost_ack(*args, **kwargs):
        await start(*args, **kwargs)
        raise OSError("detach")

    monkeypatch.setattr(coordinator.client, "astart", lost_ack)
    with pytest.raises(OSError):
        await run(coordinator, spec)
    monkeypatch.setattr(coordinator.client, "astart", start)
    with pytest.raises(SandboxError, match="different input"):
        await coordinator.arun(
            spec.session_id,
            agent_id=spec.agent_id,
            env=spec.env,
            run_id="first",
            input="changed",
            sdk="fixture",
            user_id="user",
        )
    with pytest.raises(SandboxError, match="configuration changed"):
        await run(coordinator, spec, config={"delay": 1})
    assert (await run(coordinator, spec)).status == RunStatus.completed


async def test_cancelled_admission_does_not_strand_its_lease(system, monkeypatch):
    coordinator, spec, root = system
    claim = coordinator.store.aclaim
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed_ack(**kwargs):
        state = await claim(**kwargs)
        entered.set()
        await release.wait()
        return state

    monkeypatch.setattr(coordinator.store, "aclaim", delayed_ack)
    task = asyncio.create_task(run(coordinator, spec))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0.05)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    monkeypatch.setattr(coordinator.store, "aclaim", claim)
    assert (await run(coordinator, spec)).status == RunStatus.completed
    assert await recovered_effects(coordinator, root) == ["first"]


async def test_crash_after_provision_replaces_unbound_computer_before_execution(system, monkeypatch):
    coordinator, spec, root = system
    write = coordinator.store._write_record
    failed = []

    def fail_binding(connection, lease, record):
        if record.get("computer") and not failed:
            failed.append(True)
            raise OSError("lost provisioning commit")
        return write(connection, lease, record)

    monkeypatch.setattr(coordinator.store, "_write_record", fail_binding)
    with pytest.raises(OSError, match="provisioning"):
        await run(coordinator, spec)
    state = await binding(coordinator)
    orphan = await coordinator.provider.afind(
        spec.session_id, agent_id=spec.agent_id, generation=state["record"]["generation"], env=spec.env
    )
    assert orphan is not None and state["record"]["computer"] is None
    monkeypatch.setattr(coordinator.store, "_write_record", write)
    assert (await run(coordinator, spec)).status == RunStatus.completed
    assert await coordinator.provider.aget(orphan.provider_ref) is None
    assert await recovered_effects(coordinator, root) == ["first"]


async def test_native_mirror_failure_cannot_publish_success(system, monkeypatch):
    coordinator, spec, _ = system
    poll = coordinator.client.apoll

    async def warning(*args, **kwargs):
        page = await poll(*args, **kwargs)
        if page.result is not None and page.result["type"] == "execution_finished":
            page.result["run"]["metadata"] = {"warnings": [{"type": "transcript_persistence_failed"}]}
            page.result["run"]["tools"] = [{"tool_name": "fixture", "tool_call_id": "effect", "result": "already ran"}]
        return page

    monkeypatch.setattr(coordinator.client, "apoll", warning)
    output = await run(coordinator, spec)
    assert output.status == RunStatus.error and "transcript persistence" in output.content
    assert output.tools[0].result == "already ran"
    assert output.metadata["retryable"] is False
    assert (await binding(coordinator))["record"]["checkpoint"] is None
