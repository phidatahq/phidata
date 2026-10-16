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
from tests.integration.db.test_company_patches import checkpoint, local_repository  # noqa: F401

URL = "https://github.com/octocat/Hello-World"
PIN = {"url": URL, "branch": "master", "commit": "a" * 40}


@pytest_asyncio.fixture
async def sandbox_system(system):  # noqa: F811
    client, db, worker, os, components = system
    agent = FixtureAgent(
        id="engineer",
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
async def test_successful_retry_establishes_missing_pin(sandbox_system, first_status, checkpoint):  # noqa: F811
    client, db, worker, _, agent = sandbox_system
    fixture_agent, _, commit, capture, _ = checkpoint
    agent.sandbox = fixture_agent.sandbox
    pin = {**PIN, "commit": commit}
    reference = capture()
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
                "agent_id": agent.id,
                "metadata": {"sandbox": {"repository": pin, "checkpoint": reference}},
            },
        )

    agent.aget_run_output = output
    await _project_run(worker, second_job, "completed")
    result = await _call(db, "get_task", task["id"])
    assert result["status"] == "in_review"
    assert result["result"]["status"] == "COMPLETED"
    assert result["metadata"]["checkout"] == {"source_id": task["id"], **pin}
    assert result["session_id"] == failed["session_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["backlog", "reassigned", "archived", "new_reservation"])
async def test_live_job_blocks_after_task_mutation(sandbox_system, mutation):
    client, db, worker, _, _ = sandbox_system
    first = await engineering_task(client, db)
    second = await engineering_task(client, db)
    path = "/company/tasks/" + first["id"]
    response = await client.post(path + "/runs")
    assert response.status_code == 202, response.text
    job = await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds)
    assert job["id"] == response.json()["run_id"]
    second_path = "/company/tasks/" + second["id"] + "/runs"
    assert (await client.post(second_path)).status_code == 409
    assert (
        await client.post(path + "/transitions", json={"target": "backlog", "reason": "Edit work"})
    ).status_code == 200
    if mutation in {"reassigned", "new_reservation"}:
        ready = await client.post(
            path + "/transitions",
            json={"target": "ready", "reason": "New executor", "executor_type": "agent", "executor_id": "writer"},
        )
        assert ready.status_code == 200, ready.text
        if mutation == "new_reservation":
            value = await _call(db, "get_task", first["id"])
            await _call(db, "start_task_run", first["id"], 2, value["transitions"], run_db_id=worker.config.db.id)
    elif mutation == "archived":
        assert (await client.delete(path)).status_code == 204
    blocked = await client.post(second_path)
    assert blocked.status_code == 409 and "live job" in blocked.text, blocked.text
    assert (await worker.store.get_job(job["id"]))["status"] == "running"
    await worker.store.complete_job(job["id"], worker.worker_id, job["attempt"], "cancelled")
    allowed = await client.post(second_path)
    assert allowed.status_code == 202, allowed.text


@pytest.mark.asyncio
async def test_ticketless_run_blocks_after_reassignment(sandbox_system):
    client, db, worker, _, agent = sandbox_system
    first = await engineering_task(client, db)
    second = await engineering_task(client, db)
    path = "/company/tasks/" + first["id"]
    response = await client.post(path + "/runs")
    assert response.status_code == 202, response.text
    run_id = response.json()["run_id"]
    run = agent.db.get_run(run_id, deserialize=False)
    data = {**run["run_data"], "status": "RUNNING"}
    agent.db.upsert_run(data, session_id=run["session_id"])
    table = worker.config.db._get_table("jobs")
    with worker.config.db.Session() as session, session.begin():
        session.execute(table.delete().where(table.c.id == run_id))
    assert (
        await client.post(path + "/transitions", json={"target": "backlog", "reason": "Edit work"})
    ).status_code == 200
    assert (
        await client.post(
            path + "/transitions",
            json={"target": "ready", "reason": "New executor", "executor_type": "agent", "executor_id": "writer"},
        )
    ).status_code == 200
    second_path = "/company/tasks/" + second["id"] + "/runs"
    blocked = await client.post(second_path)
    assert blocked.status_code == 409 and "live job" in blocked.text, blocked.text
    agent.db.upsert_run({**data, "status": "CANCELLED"}, session_id=run["session_id"])
    assert (await client.post(second_path)).status_code == 202


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
    assert listing.await_count == (1 if authorized else 0)
