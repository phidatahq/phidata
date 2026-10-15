"""Real AgentOS HTTP/queue/Redis/Postgres/Docker execution, with a fixture harness."""

import asyncio
import os
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select, update

from agno.db.postgres import PostgresDb
from agno.job_queue.config import QueueConfig, RedisCoordination
from agno.os import AgentOS
from agno.sandbox import _harness
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.fixture import FixtureAgent

URL = os.environ.get("AGNO_TEST_SANDBOX_DB_URL")
IMAGE = os.environ.get("AGNO_TEST_RUNTIME_IMAGE")
REDIS = os.environ.get("AGNO_TEST_REDIS_URL")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not URL or not IMAGE or not REDIS, reason="Enable dedicated Docker, Postgres and Redis"),
]


@pytest_asyncio.fixture
async def service(tmp_path):
    import redis
    import redis.asyncio

    import agno.os.event_streams as streams
    import agno.run.cancel as cancel
    from agno.run.cancellation_management.in_memory_cancellation_manager import InMemoryRunCancellationManager

    old = (
        streams._event_stream,
        streams._event_stream_explicitly_set,
        cancel._cancellation_manager,
        cancel._cancellation_manager_explicitly_set,
    )
    streams._event_stream, streams._event_stream_explicitly_set = None, False
    cancel._cancellation_manager, cancel._cancellation_manager_explicitly_set = InMemoryRunCancellationManager(), False
    suffix = uuid4().hex[:12]
    prefix = "sandbox-http-" + suffix
    redis_sync, redis_async = redis.Redis.from_url(REDIS), redis.asyncio.Redis.from_url(REDIS)
    db = PostgresDb(
        db_url=URL,
        session_table="http_sessions_" + suffix,
        runs_table="http_runs_" + suffix,
        job_table="http_jobs_" + suffix,
        sandbox_table="http_bindings_" + suffix,
    )
    provider = DockerSandbox(
        IMAGE,
        namespace=prefix,
        memory_mb=512,
        workspace_mb=32,
        env={"AGNO_SANDBOX_TEST_RUNTIME": "1"},
        checkpoints=FileCheckpointStore(tmp_path / "objects"),
    )
    handles = []
    original = provider.acreate

    async def create(session_id, **kwargs):
        handle = await original(session_id, **kwargs)
        handles.append(handle)
        return handle

    provider.acreate = create  # type: ignore[method-assign]
    agent = FixtureAgent(id="coder", sandbox=provider)
    other = FixtureAgent(id="other", sandbox=provider)
    config = QueueConfig(
        durable=True,
        db=db,
        redis=RedisCoordination(sync_client=redis_sync, async_client=redis_async, key_prefix=prefix),
        poll_interval=0.05,
        max_attempts=2,
        retry_delay_seconds=0,
        stop_timeout_seconds=1,
    )
    app = AgentOS(id=prefix, agents=[agent, other], db=db, queue=config, telemetry=False).get_app()
    try:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=30
            ) as client:
                yield client, agent, app, handles
    finally:
        for handle in handles:
            await provider.adestroy(handle)
        with db.db_engine.begin() as connection:
            for table_type in ("sandbox_bindings", "jobs", "runs", "sessions"):
                table = db._get_table(table_type)
                if table is not None:
                    table.drop(connection, checkfirst=True)
        db.db_engine.dispose()
        keys = await redis_async.keys(prefix + "*")
        if keys:
            await redis_async.delete(*keys)
        await redis_async.aclose()
        redis_sync.close()
        (
            streams._event_stream,
            streams._event_stream_explicitly_set,
            cancel._cancellation_manager,
            cancel._cancellation_manager_explicitly_set,
        ) = old


async def settled(app, run_id):
    async def wait():
        while True:
            job = await app.state.queue_worker.store.get_job(run_id)
            if job["status"] in ("completed", "failed", "cancelled"):
                return job
            await asyncio.sleep(0.05)

    return await asyncio.wait_for(wait(), 25)


async def test_foreground_request_uses_durable_worker_and_committed_checkpoint(service):
    client, agent, app, handles = service
    response = await client.post(
        "/agents/coder/runs", data={"message": "first", "session_id": "session", "stream": "false"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "COMPLETED" and body["content"] == "first", body
    assert body["metadata"]["sandbox"]["checkpoint"]
    job = await app.state.queue_worker.store.get_job(body["run_id"])
    assert job["status"] == "completed" and job["attempt"] == 1
    assert job["payload"]["serialize_session"] is True
    assert handles
    assert all(
        value is None
        for value in await asyncio.gather(*(_harness.coordinator(agent).provider.aget(h.provider_ref) for h in handles))
    )


async def test_background_acceptance_poll_and_idempotency(service):
    client, agent, app, _ = service
    data = {"message": "background", "session_id": "session", "stream": "false", "background": "true"}
    first = await client.post("/agents/coder/runs", data=data, headers={"Idempotency-Key": "one"})
    assert first.status_code == 202, first.text
    second = await client.post("/agents/coder/runs", data=data, headers={"Idempotency-Key": "one"})
    assert second.status_code == 202 and second.json()["run_id"] == first.json()["run_id"]
    job = await settled(app, first.json()["run_id"])
    assert job["status"] == "completed", job
    result = await agent.aget_run_output(job["id"], "session")
    assert result.content == "background" and result.metadata["sandbox"]["checkpoint"]


async def test_streaming_request_uses_indexed_queue_events(service):
    client, agent, _, _ = service
    response = await client.post(
        "/agents/coder/runs", data={"message": "stream", "session_id": "session", "stream": "true"}
    )
    assert response.status_code == 200, response.text
    assert "RunContent" in response.text and "RunCompleted" in response.text and "event_index" in response.text
    session = await agent.aget_session("session")
    assert session.session_data["sandbox"]["checkpoint"]


async def test_queued_same_session_turns_do_not_spend_attempts_on_contention(service):
    client, agent, app, _ = service
    agent.delay = 0.3

    async def submit(message):
        response = await client.post(
            "/agents/coder/runs",
            data={"message": message, "session_id": "session", "stream": "false", "background": "true"},
        )
        assert response.status_code == 202, response.text
        return response.json()["run_id"]

    ids = await asyncio.gather(submit("one"), submit("two"))
    jobs = await asyncio.gather(*(settled(app, run_id) for run_id in ids))
    assert all(job["status"] == "completed" and job["attempt"] == 1 for job in jobs), jobs
    assert len((await agent.aget_session("session")).runs) == 2


async def test_checkpoint_outage_retries_finalization_only(service, monkeypatch):
    client, agent, app, _ = service
    capture = _harness.coordinator(agent).transfer.acapture
    calls = []

    async def fail_once(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise OSError("injected storage outage")
        return await capture(*args, **kwargs)

    monkeypatch.setattr(_harness.coordinator(agent).transfer, "acapture", fail_once)
    response = await client.post(
        "/agents/coder/runs",
        data={"message": "retry", "session_id": "session", "stream": "false", "background": "true"},
    )
    assert response.status_code == 202, response.text
    job = await settled(app, response.json()["run_id"])
    assert job["status"] == "completed" and job["attempt"] == 2, job
    row = await _harness.coordinator(agent).store._transaction(
        lambda c: c.execute(select(_harness.coordinator(agent).store.bindings)).mappings().one()
    )
    from agno.sandbox.checkpoint import CheckpointRef

    destination = _harness.coordinator(agent).transfer.store.root / "verify"
    await _harness.coordinator(agent).transfer.store.arestore(CheckpointRef(**row["record"]["checkpoint"]), destination)
    assert (destination / "workspace/fixture-effects.txt").read_text().splitlines() == [job["id"]]


async def test_retained_events_replay_after_live_keys_expire(service):
    from agno.os.event_streams import get_event_stream

    client, agent, app, _ = service
    response = await client.post(
        "/agents/coder/runs", data={"message": "retain", "session_id": "session", "stream": "false"}
    )
    assert response.status_code == 200, response.text
    run_id = response.json()["run_id"]
    await settled(app, run_id)
    run = await agent.aget_run_output(run_id, "session")
    assert run.events and any(event.event == "RunCompleted" and event.event_index is not None for event in run.events)
    await get_event_stream().cleanup_run(run_id)
    replay = await client.post(f"/agents/coder/runs/{run_id}/resume", data={"session_id": "session"})
    assert replay.status_code == 200 and "RunCompleted" in replay.text and "event_index" in replay.text, replay.text


async def test_cancel_active_run_removes_compute_before_terminal(service):
    client, agent, app, handles = service
    agent.delay = 10
    response = await client.post(
        "/agents/coder/runs",
        data={"message": "cancel", "session_id": "session", "stream": "false", "background": "true"},
    )
    run_id = response.json()["run_id"]

    async def allocated():
        while not handles:
            await asyncio.sleep(0.05)

    await asyncio.wait_for(allocated(), 10)
    cancelled = await client.post(f"/agents/coder/runs/{run_id}/cancel", params={"session_id": "session"})
    assert cancelled.status_code == 200, cancelled.text
    job = await settled(app, run_id)
    assert job["status"] == "cancelled", job
    assert all(
        value is None
        for value in await asyncio.gather(*(_harness.coordinator(agent).provider.aget(h.provider_ref) for h in handles))
    )
    run = await agent.aget_run_output(run_id, "session")
    assert run.status == "CANCELLED"


async def test_exhausted_checkpoint_retries_clean_up_before_failing(service, monkeypatch):
    client, agent, app, handles = service

    async def unavailable(*args, **kwargs):
        raise OSError("checkpoint storage unavailable")

    monkeypatch.setattr(_harness.coordinator(agent).transfer, "acapture", unavailable)
    response = await client.post(
        "/agents/coder/runs",
        data={"message": "outage", "session_id": "session", "stream": "false", "background": "true"},
    )
    job = await settled(app, response.json()["run_id"])
    assert job["status"] == "failed" and job["attempt"] == 2, job
    assert len(handles) == 1
    assert await _harness.coordinator(agent).provider.aget(handles[0].provider_ref) is None
    row = await _harness.coordinator(agent).store._transaction(
        lambda c: c.execute(select(_harness.coordinator(agent).store.bindings)).mappings().one()
    )
    assert row["record"]["phase"] == "idle" and row["record"]["computer"] is None


async def test_cancel_between_attempts_cleans_up_before_ticket_settlement(service, monkeypatch):
    client, agent, app, handles = service
    monkeypatch.setattr(app.state.queue_worker, "_retry_delay", lambda attempt: 30)

    async def unavailable(*args, **kwargs):
        raise OSError("checkpoint storage unavailable")

    monkeypatch.setattr(_harness.coordinator(agent).transfer, "acapture", unavailable)
    response = await client.post(
        "/agents/coder/runs",
        data={"message": "cancel retry", "session_id": "session", "stream": "false", "background": "true"},
    )
    run_id = response.json()["run_id"]

    async def waiting():
        while True:
            job = await app.state.queue_worker.store.get_job(run_id)
            if job["status"] == "queued" and job["attempt"] == 1:
                return
            await asyncio.sleep(0.05)

    await asyncio.wait_for(waiting(), 15)
    assert await _harness.coordinator(agent).provider.aget(handles[0].provider_ref) is not None
    response = await client.post(f"/agents/coder/runs/{run_id}/cancel", params={"session_id": "session"})
    assert response.status_code == 200, response.text
    assert (await settled(app, run_id))["status"] == "cancelled"
    assert await _harness.coordinator(agent).provider.aget(handles[0].provider_ref) is None


async def test_sdk_background_uses_same_registered_queue(service):
    _, agent, app, _ = service
    pending = await agent.arun("sdk", session_id="session", background=True)
    assert pending.status == "PENDING"
    assert (await settled(app, pending.run_id))["status"] == "completed"


async def test_missing_durable_queue_rejects_before_allocating(service):
    _, agent, _, handles = service
    app = AgentOS(id="no-queue", agents=[agent], db=agent.db, telemetry=False).get_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/agents/coder/runs", data={"message": "no", "session_id": "session", "stream": "false"}
        )
    assert response.status_code == 400 and "durable queue" in response.text
    assert not handles


async def test_cancel_detached_direct_sdk_run_retires_computer(service):
    _, agent, _, handles = service
    agent.delay = 10
    task = asyncio.create_task(agent.arun("detach", session_id="session", run_id="direct"))

    async def allocated():
        while not handles:
            await asyncio.sleep(0.05)

    await asyncio.wait_for(allocated(), 10)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await _harness.coordinator(agent).provider.aget(handles[0].provider_ref) is not None
    await agent.acancel_run("direct")
    assert await _harness.coordinator(agent).provider.aget(handles[0].provider_ref) is None
    assert (await agent.aget_run_output("direct", "session")).status == "CANCELLED"


async def test_timed_out_attempt_is_retried_on_new_compute(service, monkeypatch):
    client, agent, app, handles = service
    agent.delay = 4
    monkeypatch.setattr(app.state.queue_worker.config, "timeout_seconds", 2)
    response = await client.post(
        "/agents/coder/runs",
        data={"message": "slow", "session_id": "session", "stream": "false", "background": "true"},
    )
    job = await settled(app, response.json()["run_id"])
    # Both attempts time out; the second must have executed again, not replayed the first ERROR.
    assert job["status"] == "failed" and job["attempt"] == 2, job
    assert "timeout_seconds" in (job.get("error") or ""), job
    assert len(handles) == 2, handles
    assert all(
        value is None
        for value in await asyncio.gather(*(_harness.coordinator(agent).provider.aget(h.provider_ref) for h in handles))
    )


async def test_direct_run_keeps_the_agent_name(service):
    _, agent, _, _ = service
    agent.name = "Coder"
    result = await agent.arun("named", session_id="session", run_id="named")
    assert result.status == "COMPLETED" and result.agent_name == "Coder"
    assert (await agent.aget_run_output("named", "session")).agent_name == "Coder"


async def test_remote_cancel_fences_the_worker_without_failing_its_ticket(service):
    client, agent, app, handles = service
    agent.delay = 20
    app.state.queue_worker.config.max_attempts = 1
    response = await client.post(
        "/agents/coder/runs",
        data={"message": "cancel", "session_id": "session", "stream": "false", "background": "true"},
    )
    run_id = response.json()["run_id"]

    async def allocated():
        while not handles:
            await asyncio.sleep(0.05)

    await asyncio.wait_for(allocated(), 10)
    # No live handle here, so this takes the path a cancel on another replica takes: fence the
    # worker's lease and retire its computer. The worker's attempt then fails with a lost lease
    # or a dead transport, which must settle the ticket as cancelled, not failed.
    await agent.acancel_run(run_id)
    job = await settled(app, run_id)
    assert job["status"] == "cancelled", job
    assert (await agent.aget_run_output(run_id, "session")).status == "CANCELLED"
    for handle in handles:
        assert await _harness.coordinator(agent).provider.aget(handle.provider_ref) is None


# --- Idempotency-Key: the shared duplicate-key contract -------------------------------------
# A key is a retry token, not a request fingerprint. As on the agent and team routes, a duplicate
# answers with the ORIGINAL run (whatever else the retry carries) unless the key was used on
# another component; the user is part of the key's namespace.


def queued_rows(agent, key):
    table = agent.db._get_table("jobs")
    with agent.db.db_engine.begin() as connection:
        return connection.execute(
            select(func.count()).select_from(table).where(table.c.idempotency_key == key)
        ).scalar_one()


async def submit_keyed(client, key, *, message="first", session="session", user_id=None, **form):
    data = {"message": message, "session_id": session, "stream": "false", "background": "true", **form}
    if user_id is not None:
        data["user_id"] = user_id
    return await client.post("/agents/coder/runs", data=data, headers={"Idempotency-Key": key})


async def test_duplicate_key_returns_the_original_run_whatever_the_retry_carries(service):
    client, agent, app, handles = service
    original = await submit_keyed(client, "same-key")
    assert original.status_code == 202, original.text
    run_id = original.json()["run_id"]
    assert (await settled(app, run_id))["status"] == "completed"
    identical = await submit_keyed(client, "same-key")
    changed_input = await submit_keyed(client, "same-key", message="changed")
    other_session = await submit_keyed(client, "same-key", session="other-session")
    for retry in (identical, changed_input, other_session):
        assert retry.status_code == 202, retry.text
        assert retry.json()["run_id"] == run_id
        assert retry.json()["session_id"] == "session"
    assert queued_rows(agent, "same-key") == 1 and len(handles) == 1
    assert (await agent.aget_run_output(run_id, "session")).content == "first"
    assert await agent.aget_run_output(run_id, "other-session") is None


async def test_fields_the_queue_adds_to_the_payload_do_not_break_a_retry(service):
    client, agent, app, _ = service
    original = await submit_keyed(client, "stamped")
    run_id = original.json()["run_id"]
    assert (await settled(app, run_id))["status"] == "completed"
    table = agent.db._get_table("jobs")
    payload = (await app.state.queue_worker.store.get_job(run_id))["payload"]
    with agent.db.db_engine.begin() as connection:
        connection.execute(
            update(table).where(table.c.id == run_id).values(payload={**payload, "a_field_the_queue_may_add": 1})
        )
    retry = await submit_keyed(client, "stamped")
    assert retry.status_code == 202 and retry.json()["run_id"] == run_id
    assert queued_rows(agent, "stamped") == 1


async def test_a_key_used_on_another_component_is_refused_without_a_new_run(service):
    client, agent, app, handles = service
    original = await submit_keyed(client, "cross")
    run_id = original.json()["run_id"]
    assert (await settled(app, run_id))["status"] == "completed"
    crossed = await client.post(
        "/agents/other/runs",
        data={"message": "first", "session_id": "session", "stream": "false", "background": "true"},
        headers={"Idempotency-Key": "cross"},
    )
    assert crossed.status_code == 409 and "different component" in crossed.json()["detail"]
    assert "coder" not in crossed.json()["detail"]
    assert queued_rows(agent, "cross") == 1 and len(handles) == 1


async def test_the_same_key_under_different_users_is_two_independent_runs(service):
    client, agent, app, handles = service
    alice = await submit_keyed(client, "shared", session="alice-session", user_id="alice")
    bob = await submit_keyed(client, "shared", session="bob-session", user_id="bob")
    assert alice.status_code == 202 and bob.status_code == 202, (alice.text, bob.text)
    assert alice.json()["run_id"] != bob.json()["run_id"]
    for run in (alice, bob):
        assert (await settled(app, run.json()["run_id"]))["status"] == "completed"
    for run, user in ((alice, "alice"), (bob, "bob")):
        retry = await submit_keyed(client, "shared", session=run.json()["session_id"], user_id=user)
        assert retry.json()["run_id"] == run.json()["run_id"]
    assert queued_rows(agent, "shared") == 2 and len(handles) == 2
    assert await agent.aget_run_output(alice.json()["run_id"], "alice-session", user_id="bob") is None


async def test_concurrent_identical_submissions_create_and_execute_one_run(service):
    client, agent, app, handles = service
    background = await asyncio.gather(*(submit_keyed(client, "burst") for _ in range(5)))
    assert {response.status_code for response in background} == {202}, [r.text for r in background]
    assert len({response.json()["run_id"] for response in background}) == 1
    assert (await settled(app, background[0].json()["run_id"]))["status"] == "completed"
    assert queued_rows(agent, "burst") == 1 and len(handles) == 1
    foreground = await asyncio.gather(
        *(submit_keyed(client, "burst-foreground", background="false", message="again") for _ in range(3))
    )
    assert {response.status_code for response in foreground} == {200}, [response.text for response in foreground]
    assert len({response.json()["run_id"] for response in foreground}) == 1
    assert queued_rows(agent, "burst-foreground") == 1 and len(handles) == 2


async def test_a_streamed_duplicate_attaches_to_the_original_run(service):
    client, agent, app, handles = service

    async def stream(message):
        return await client.post(
            "/agents/coder/runs",
            data={"message": message, "session_id": "session", "stream": "true"},
            headers={"Idempotency-Key": "streamed"},
        )

    first = await stream("first")
    assert first.status_code == 200 and "RunCompleted" in first.text
    duplicate = await stream("a different message")
    assert duplicate.status_code == 200 and "RunCompleted" in duplicate.text and "first" in duplicate.text
    assert "a different message" not in duplicate.text
    assert queued_rows(agent, "streamed") == 1 and len(handles) == 1
