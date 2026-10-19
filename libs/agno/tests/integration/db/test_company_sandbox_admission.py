"""Model-free sandbox admission and retry regressions on all four Company stores."""

from types import SimpleNamespace

import pytest
import pytest_asyncio

from agno.company.execution import _call, _project_run
from agno.job_queue import QueueConfig
from agno.sandbox import Repository
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.fixture import FixtureAgent
from tests.integration.db.test_company_execution_parity import accepted, system  # noqa: F401, F811

URL = "https://github.com/octocat/Hello-World"
PIN = {"url": URL, "branch": "master", "commit": "a" * 40}


@pytest_asyncio.fixture
async def sandbox_system(system, monkeypatch):  # noqa: F811
    import agno.os.event_streams as streams
    import agno.run.cancel as cancel

    # Queue configuration can replace process defaults; restore them after each case.
    monkeypatch.setattr(streams, "_event_stream", streams._event_stream)
    monkeypatch.setattr(streams, "_event_stream_explicitly_set", streams._event_stream_explicitly_set)
    monkeypatch.setattr(cancel, "_cancellation_manager", cancel._cancellation_manager)
    monkeypatch.setattr(cancel, "_cancellation_manager_explicitly_set", cancel._cancellation_manager_explicitly_set)
    client, db, worker, os, components = system
    agent = FixtureAgent(
        id="engineer",
        max_concurrent_runs=1,
        db=worker.config.db,
        sandbox=DockerSandbox("unused", env={"AGNO_SANDBOX_TEST_RUNTIME": "1"}),
        repository=Repository(URL, "master"),
    )
    os.agents.append(agent)
    os.registry.agents.append(agent)
    os.dbs[agent.db.id] = [agent.db]
    components["engineer"] = agent
    worker.config = QueueConfig(durable=True, db=worker.config.db, redis="redis://localhost:6379/0", max_attempts=1)
    yield client, db, worker, os, agent


async def engineering_task(client, db):
    task = await accepted(client)
    path = "/company/tasks/" + task["id"]
    assert (
        await client.post(path + "/transitions", json={"target": "backlog", "reason": "Select engineer"})
    ).status_code == 200
    await _call(
        db,
        "create_source",
        {"id": task["id"], "product_id": task["product_id"], "type": "git", "reference": URL, "created_at": 1},
    )
    ready = await client.post(
        path + "/transitions",
        json={"target": "ready", "reason": "Approved", "executor_type": "agent", "executor_id": "engineer"},
    )
    assert ready.status_code == 200, ready.text
    return ready.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("first_status", ["failed", "cancelled"])
async def test_successful_retry_establishes_missing_pin(sandbox_system, first_status):
    client, db, worker, _, agent = sandbox_system
    task = await engineering_task(client, db)
    path = "/company/tasks/" + task["id"]
    first = await client.post(path + "/runs")
    assert first.status_code == 202, first.text
    job = await worker.store.get_job(first.json()["run_id"])
    await _project_run(worker, job, first_status, "Transient first attempt")
    await worker.store.cancel_job(job["id"])
    failed = await _call(db, "get_task", task["id"])
    assert failed["metadata"] is None
    second = await client.post(path + "/runs", json={"attempt": 2})
    assert second.status_code == 202, second.text
    second_job = await worker.store.get_job(second.json()["run_id"])

    async def output(*args, **kwargs):
        return SimpleNamespace(
            status="COMPLETED",
            to_dict=lambda: {
                "run_id": second_job["id"],
                "status": "COMPLETED",
                "content": "Successful retry",
                "metadata": {"sandbox": {"repository": PIN}},
            },
        )

    agent.aget_run_output = output
    await _project_run(worker, second_job, "completed")
    result = await _call(db, "get_task", task["id"])
    assert result["status"] == "in_review"
    assert result["result"]["status"] == "COMPLETED"
    assert result["metadata"]["checkout"] == {"source_id": task["id"], **PIN}
    assert result["session_id"] == failed["session_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("authorized", [True, False])
async def test_start_checks_permission_once_before_admission(sandbox_system, monkeypatch, authorized):
    from unittest.mock import AsyncMock

    from fastapi import HTTPException

    import agno.os.routers.company.runs as routes

    client, db, worker, _, _ = sandbox_system
    task = await engineering_task(client, db)
    permission = AsyncMock(side_effect=None if authorized else HTTPException(403, "Denied"))
    listing = AsyncMock(wraps=worker.store.list_jobs)
    monkeypatch.setattr(routes, "_require_endpoint_permission", permission)
    monkeypatch.setattr(worker.store, "list_jobs", listing)
    response = await client.post("/company/tasks/" + task["id"] + "/runs")
    assert response.status_code == (202 if authorized else 403), response.text
    permission.assert_awaited_once()
    assert listing.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy", [False, True])
async def test_settled_retired_executor_does_not_block_admission(sandbox_system, legacy):
    from agno.db.base import AsyncBaseDb
    from tests.integration.db.test_company_execution_parity import execute

    client, db, worker, os, _ = sandbox_system
    old = await accepted(client)
    other = await engineering_task(client, db)
    path = "/company/tasks/" + old["id"]
    assert (await client.post(path + "/runs")).status_code == 202
    assert (await execute(worker))["status"] == "completed"
    assert (await client.post(path + "/transitions", json={"target": "done", "reason": "Accepted"})).status_code == 200
    old = await _call(db, "get_task", old["id"])
    table = worker.config.db._get_table("jobs")
    with worker.config.db.Session() as session, session.begin():
        session.execute(table.delete().where(table.c.id == old["job_id"]))
    if legacy:
        history = [{k: v for k, v in entry.items() if k != "run_db_id"} for entry in old["transitions"]]
        if isinstance(db, AsyncBaseDb):
            table = await db._get_table("tasks")
            async with db.db_engine.begin() as connection:
                await connection.execute(table.update().where(table.c.id == old["id"]).values(transitions=history))
        else:
            table = db._get_table("tasks")
            with db.db_engine.begin() as connection:
                connection.execute(table.update().where(table.c.id == old["id"]).values(transitions=history))
    os.dbs.pop(db.id, None)
    os.registry.agents[:] = [agent for agent in os.registry.agents if agent.id != "writer"]
    started = await client.post("/company/tasks/" + other["id"] + "/runs")
    assert started.status_code == 202, started.text


@pytest.mark.asyncio
async def test_checkout_projection_error_can_retry_after_source_repair(sandbox_system):
    client, db, worker, _, agent = sandbox_system
    task = await engineering_task(client, db)
    path = "/company/tasks/" + task["id"]
    assert (await client.post(path + "/runs")).status_code == 202
    job = await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds)
    assert (await client.delete("/company/sources/" + task["id"])).status_code == 204
    run = agent.db.get_run(job["id"], deserialize=False)
    data = {**run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {"repository": PIN}}}
    agent.db.upsert_run(data, session_id=run["session_id"])
    assert await worker._asettle_ticket(job["id"], job["attempt"], "completed")
    failed = await _call(db, "get_task", task["id"])
    assert failed["result"]["status"] == "ERROR"
    assert (await worker.store.get_job(job["id"]))["status"] == "completed"
    source = await client.post(
        "/company/sources", json={"product_id": task["product_id"], "type": "git", "reference": URL}
    )
    assert source.status_code == 201
    response = await client.post(path + "/runs", json={"attempt": 2})
    assert response.status_code == 202, response.text
    second = await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds)
    second_run = agent.db.get_run(second["id"], deserialize=False)
    agent.db.upsert_run(
        {**second_run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {"repository": PIN}}},
        session_id=run["session_id"],
    )
    assert await worker._asettle_ticket(second["id"], second["attempt"], "completed")
    completed = await _call(db, "get_task", task["id"])
    assert completed["status"] == "in_review" and completed["metadata"]["checkout"]["commit"] == PIN["commit"]
    assert (
        await client.post(path + "/transitions", json={"target": "backlog", "reason": "Reassign"})
    ).status_code == 200
    original = agent.repository
    agent.repository = Repository("https://github.com/other/repository", "master")
    await _call(
        db,
        "create_source",
        {
            "id": "other-repo",
            "product_id": task["product_id"],
            "type": "git",
            "reference": agent.repository.url,
            "created_at": 1,
        },
    )
    refused = await client.post(
        path + "/transitions",
        json={"target": "ready", "reason": "Different repository", "executor_type": "agent", "executor_id": "engineer"},
    )
    assert refused.status_code == 409 and "already pinned" in refused.text, refused.text
    assert (await _call(db, "get_task", task["id"]))["metadata"] == completed["metadata"]
    agent.repository = original


@pytest.mark.asyncio
@pytest.mark.parametrize("second_pin", ["same", "different", "missing"])
async def test_recovery_projects_and_verifies_checkout(sandbox_system, monkeypatch, second_pin):
    from unittest.mock import AsyncMock

    from agno.company.execution import _reconcile_task_run, _recover_task
    from tests.integration.db.test_company_failure_recovery import delete_ticket

    client, db, worker, os, agent = sandbox_system
    task = await engineering_task(client, db)
    path = "/company/tasks/" + task["id"] + "/runs"
    first = await client.post(path)
    assert first.status_code == 202, first.text
    reserved = await _call(db, "get_task", task["id"])
    run = agent.db.get_run(reserved["job_id"], deserialize=False)
    agent.db.upsert_run(
        {**run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {"repository": PIN}}},
        session_id=task["session_id"],
    )
    delete_ticket(worker, reserved["job_id"])
    with monkeypatch.context() as recovery:
        recovery.setattr(
            worker.store, "enqueue_job", AsyncMock(side_effect=AssertionError("Recovery must not enqueue"))
        )
        outcome = await _recover_task(os, worker, reserved)
    assert outcome["action"] == "reconciled"
    saved = await _call(db, "get_task", task["id"])
    checkout = {"source_id": task["id"], **PIN}
    assert saved["metadata"]["checkout"] == checkout
    assert saved["result"]["status"] == "COMPLETED" and saved["status"] == "in_review"
    current = await _call(db, "get_task", task["id"])
    if current["status"] == "in_review":
        assert (
            await client.post(
                path.removesuffix("/runs") + "/transitions", json={"target": "ready", "reason": "Revise result"}
            )
        ).status_code == 200
    second = await client.post(path, json={"attempt": 2})
    assert second.status_code == 202, second.text
    reserved = await _call(db, "get_task", task["id"])
    assert reserved["session_id"] == task["session_id"]
    run = agent.db.get_run(reserved["job_id"], deserialize=False)
    ticket = await worker.store.get_job(reserved["job_id"])
    assert ticket["payload"]["kwargs"]["metadata"]["repository"] == {"commit": PIN["commit"]}
    pin = {**PIN, "commit": "b" * 40} if second_pin == "different" else PIN
    data = {**run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {}}}
    if second_pin != "missing":
        data["metadata"]["sandbox"]["repository"] = pin
    agent.db.upsert_run(data, session_id=task["session_id"])
    delete_ticket(worker, reserved["job_id"])
    with monkeypatch.context() as recovery:
        recovery.setattr(
            worker.store, "enqueue_job", AsyncMock(side_effect=AssertionError("Recovery must not enqueue"))
        )
        # Repeating the HTTP start recovers the existing run rather than submitting it.
        response = await client.post(path, json={"attempt": 2})
    assert response.status_code == 202, response.text
    saved = await _call(db, "get_task", task["id"])
    assert saved["metadata"]["checkout"] == checkout
    assert saved["result"]["status"] == ("COMPLETED" if second_pin == "same" else "ERROR")
    assert saved["status"] == ("in_review" if second_pin == "same" else "in_progress")
    if second_pin != "same":
        assert "repository pin" in saved["result"]["content"]
    # A stale recovery observation cannot replace a settled result or its pin.
    agent.db.upsert_run({**data, "metadata": {"sandbox": {"repository": PIN}}}, session_id=task["session_id"])
    stale_run = agent.db.get_run(reserved["job_id"], deserialize=False)
    assert not await _reconcile_task_run(db, agent.db, reserved, stale_run, None, worker=worker)
    assert await _call(db, "get_task", task["id"]) == saved


@pytest.mark.asyncio
async def test_recovered_retry_establishes_absent_checkout(sandbox_system):
    from agno.company.execution import _recover_task
    from tests.integration.db.test_company_failure_recovery import delete_ticket

    client, db, worker, os, agent = sandbox_system
    task = await engineering_task(client, db)
    path = "/company/tasks/" + task["id"] + "/runs"
    first = await client.post(path)
    assert first.status_code == 202, first.text
    job = await worker.store.get_job(first.json()["run_id"])
    await _project_run(worker, job, "failed", "Transient first attempt")
    await worker.store.cancel_job(job["id"])
    current = await _call(db, "get_task", task["id"])
    if current["status"] == "in_review":
        assert (
            await client.post(
                path.removesuffix("/runs") + "/transitions", json={"target": "ready", "reason": "Revise result"}
            )
        ).status_code == 200
    second = await client.post(path, json={"attempt": 2})
    assert second.status_code == 202, second.text
    task = await _call(db, "get_task", task["id"])
    assert task["metadata"] is None
    run = agent.db.get_run(task["job_id"], deserialize=False)
    agent.db.upsert_run(
        {**run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {"repository": PIN}}},
        session_id=task["session_id"],
    )
    delete_ticket(worker, task["job_id"])
    assert (await _recover_task(os, worker, task))["action"] == "reconciled"
    saved = await _call(db, "get_task", task["id"])
    assert saved["metadata"]["checkout"] == {"source_id": task["id"], **PIN}
    assert saved["result"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_recovery_waits_for_missing_sandbox_executor(sandbox_system, monkeypatch):
    from unittest.mock import AsyncMock

    from agno.company.execution import _recover_task, _TaskRunUnavailable
    from tests.integration.db.test_company_failure_recovery import delete_ticket

    client, db, worker, os, agent = sandbox_system
    task = await engineering_task(client, db)
    assert (await client.post("/company/tasks/" + task["id"] + "/runs")).status_code == 202
    task = await _call(db, "get_task", task["id"])
    run = agent.db.get_run(task["job_id"], deserialize=False)
    agent.db.upsert_run(
        {**run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {"repository": PIN}}},
        session_id=task["session_id"],
    )
    delete_ticket(worker, task["job_id"])
    with monkeypatch.context() as unavailable:
        unavailable.setattr(worker, "_aresolve_job_component", AsyncMock(return_value=None))
        with pytest.raises(_TaskRunUnavailable, match="recovering its checkout"):
            await _recover_task(os, worker, task)
    assert await _call(db, "get_task", task["id"]) == task
    assert (await _recover_task(os, worker, task))["action"] == "reconciled"
    assert (await _call(db, "get_task", task["id"]))["metadata"]["checkout"] == {"source_id": task["id"], **PIN}


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,executor_id", [("agent", "writer"), ("team", "editors"), ("workflow", "draft")])
@pytest.mark.parametrize("pinned", [False, True])
async def test_pinned_task_refuses_non_sandboxed_reacceptance(sandbox_system, kind, executor_id, pinned):
    from agno.company.execution import _recover_task
    from tests.integration.db.test_company_failure_recovery import delete_ticket

    client, db, worker, os, agent = sandbox_system
    task = await engineering_task(client, db)
    path = "/company/tasks/" + task["id"]
    if pinned:
        assert (await client.post(path + "/runs")).status_code == 202
        reserved = await _call(db, "get_task", task["id"])
        run = agent.db.get_run(reserved["job_id"], deserialize=False)
        agent.db.upsert_run(
            {**run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {"repository": PIN}}},
            session_id=task["session_id"],
        )
        delete_ticket(worker, reserved["job_id"])
        assert (await _recover_task(os, worker, reserved))["action"] == "reconciled"
    assert (
        await client.post(path + "/transitions", json={"target": "backlog", "reason": "Reassign work"})
    ).status_code == 200
    before = await _call(db, "get_task", task["id"])
    response = await client.post(
        path + "/transitions",
        json={"target": "ready", "reason": "New executor", "executor_type": kind, "executor_id": executor_id},
    )
    if not pinned:
        assert response.status_code == 200, response.text
        assert response.json()["executor_type"] == kind and response.json()["executor_id"] == executor_id
        return
    assert response.status_code == 409 and "requires a sandboxed executor" in response.text, response.text
    assert await _call(db, "get_task", task["id"]) == before
    # A compatible executor can still reuse the pinned session and recover a retry.
    ready = await client.post(
        path + "/transitions",
        json={"target": "ready", "reason": "Keep repository", "executor_type": "agent", "executor_id": "engineer"},
    )
    assert ready.status_code == 200, ready.text
    retry = await client.post(path + "/runs", json={"attempt": 2})
    assert retry.status_code == 202, retry.text
    reserved = await _call(db, "get_task", task["id"])
    run = agent.db.get_run(reserved["job_id"], deserialize=False)
    agent.db.upsert_run(
        {**run["run_data"], "status": "COMPLETED", "metadata": {"sandbox": {"repository": PIN}}},
        session_id=task["session_id"],
    )
    delete_ticket(worker, reserved["job_id"])
    assert (await _recover_task(os, worker, reserved))["action"] == "reconciled"
    saved = await _call(db, "get_task", task["id"])
    assert saved["session_id"] == task["session_id"]
    assert saved["metadata"] == before["metadata"]
    assert saved["result"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_sandboxed_starts_wait_in_queue_across_deployments(sandbox_system):
    client, db, worker, _, _ = sandbox_system
    first, second = await engineering_task(client, db), await engineering_task(client, db)
    worker.config.deployment_id = "first"
    one = await client.post(f"/company/tasks/{first['id']}/runs")
    assert one.status_code == 202, one.text
    job = await worker.store.claim_job("worker-one", deployment_id="first")
    worker.config.deployment_id = "second"
    two = await client.post(f"/company/tasks/{second['id']}/runs")
    assert two.status_code == 202, two.text
    assert await worker.store.claim_job("worker-two", deployment_id="second") is None
    assert (await worker.store.get_job(two.json()["run_id"]))["status"] == "queued"
    assert await worker.store.complete_job(job["id"], "worker-one", job["attempt"], "completed")
    assert (await worker.store.claim_job("worker-two", deployment_id="second"))["id"] == two.json()["run_id"]


@pytest.mark.asyncio
async def test_sandbox_task_receives_bounded_context_as_attachment(sandbox_system):
    import base64
    import json

    client, db, worker, _, _ = sandbox_system
    task = await engineering_task(client, db)
    response = await client.post(f"/company/tasks/{task['id']}/runs")
    assert response.status_code == 202, response.text
    job = await worker.store.get_job(response.json()["run_id"])
    files = job["payload"]["kwargs"]["media"]
    assert len(files) == 1
    content = files[0]["content"]
    if isinstance(content, str):
        content = base64.b64decode(content)
    value = json.loads(content)
    assert value["brief"] == task["brief"]
    assert value["evidence"] == task["evidence"]
    assert {row["path"] for row in value["wiki"]} == {"brief.md", "status.md"}
    assert len(content) <= 256 * 1024
    assert "attached task-input.json" in job["payload"]["input"]


@pytest.mark.asyncio
async def test_team_delegates_to_two_sandboxed_members(sandbox_system, system, monkeypatch):  # noqa: F811
    from agno.run.agent import RunOutput
    from agno.run.base import RunStatus
    from agno.team import Team
    from tests.integration.db.test_company_execution_parity import execute
    from tests.unit.team.test_paused_member_persistence import _ScriptedModel

    client, db, worker, os, first = sandbox_system
    second = FixtureAgent(id="reviewer", db=first.db, sandbox=first.sandbox, repository=first.repository)
    calls = []

    async def draft(*args, **kwargs):
        calls.append("draft")
        return RunOutput(run_id="member-draft", content="Draft evidence", status=RunStatus.completed)

    async def review(*args, **kwargs):
        calls.append("review")
        return RunOutput(run_id="member-review", content="Reviewed evidence", status=RunStatus.completed)

    monkeypatch.setattr(first, "arun", draft)
    monkeypatch.setattr(second, "arun", review)
    model = _ScriptedModel(
        "review",
        [
            ("tool", "delegate_task_to_member", {"member_id": first.id, "task": "Draft"}, "one"),
            ("tool", "delegate_task_to_member", {"member_id": second.id, "task": "Review"}, "two"),
            ("content", "Reviewed draft"),
        ],
    )
    team = Team(id="sandbox-review", members=[first, second], model=model, db=db, telemetry=False)
    os.teams.append(team)
    os.registry.teams.append(team)
    system[4][team.id] = team
    task = await accepted(client, "team", team.id)
    response = await client.post(f"/company/tasks/{task['id']}/runs")
    assert response.status_code == 202, response.text
    assert (await execute(worker))["status"] == "completed"
    assert calls == ["draft", "review"], (
        await team.aget_run_output(response.json()["run_id"], session_id=task["session_id"])
    ).tools
    assert (await client.get(f"/company/tasks/{task['id']}")).json()["result"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_routine_may_trigger_sandboxed_agent(sandbox_system, monkeypatch):
    from agno.run.agent import RunOutput
    from agno.run.base import RunStatus
    from tests.integration.db.test_company_execution_parity import routine_executor

    client, db, worker, os, agent = sandbox_system
    task = await engineering_task(client, db)
    routine = await client.post(
        "/company/routines",
        json={
            "product_id": task["product_id"],
            "name": "Sandbox inspection",
            "instructions": "Inspect repository",
            "executor_type": "agent",
            "executor_id": agent.id,
        },
    )
    assert routine.status_code == 201, routine.text
    calls = []

    def run(input, **kwargs):
        async def result():
            calls.append(input)
            value = RunOutput(
                run_id=kwargs["run_id"],
                session_id=kwargs["session_id"],
                agent_id=agent.id,
                status=RunStatus.completed,
                content="Inspected",
                metadata={"sandbox": {"repository": PIN}},
            )
            agent.db.upsert_run(value, session_id=kwargs["session_id"])
            return value

        async def stream():
            yield await result()

        return stream() if kwargs.get("stream") else result()

    monkeypatch.setattr(agent, "arun", run)
    worker.authorization_app.state.scheduler_executor = await routine_executor((client, db, worker, os, {}))
    response = await client.post("/company/routines/" + routine.json()["id"] + "/trigger")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success", (
        response.text,
        [(job["status"], job.get("error")) for job in (await worker.store.list_jobs())[0]],
    )
    assert calls
