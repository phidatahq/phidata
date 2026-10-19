"""Simulation contracts through Company HTTP and injected tools on every SQL adapter."""

import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from agno.db.base import AsyncBaseDb
from agno.os import AgentOS, CompanyConfig
from agno.run.base import RunContext
from agno.tools.company import CompanyTools
from tests.integration.db.test_company_execution_parity import accepted, execute
from tests.integration.db.test_company_execution_parity import system as execution_system

system = execution_system


@pytest.mark.asyncio
async def test_two_deployment_prefixes_isolate_setup_and_wikis(system):
    _, db, _, _, _ = system
    suffix = uuid4().hex
    clients = [
        AsyncClient(
            transport=ASGITransport(
                app=AgentOS(db=db, company=CompanyConfig(namespace=prefix + suffix), telemetry=False).get_app()
            ),
            base_url="http://test",
        )
        for prefix in ("left/", "right/")
    ]
    try:
        ids = []
        for i, client in enumerate(clients):
            setup = await client.post("/company/setup", json={"name": "Deployment " + str(i)})
            assert setup.status_code == 201, setup.text
            ids.append(setup.json()["id"])
            path = "/company/products/" + ids[-1] + "/wiki/playbook.md"
            assert (await client.put(path, json={"content": str(i), "expected_version": 0})).status_code == 200
            assert (
                await client.put("/company/wiki/private.md", json={"content": str(i), "expected_version": 0})
            ).status_code == 200
        assert ids[0] != ids[1]
        for i, client in enumerate(clients):
            assert (await client.get("/company/wiki/private.md")).json()["content"] == str(i)
            assert (await client.get("/company/products/" + ids[1 - i] + "/wiki/playbook.md")).status_code == 404
    finally:
        for client in clients:
            await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("async_tool", [False, True])
async def test_reviewing_agent_records_actor_and_keeps_dispatch_principal(system, async_tool):
    client, db, worker, os, _ = system
    if isinstance(db, AsyncBaseDb) and not async_tool:
        pytest.skip("Async databases expose asynchronous tools")
    task = await accepted(client)
    path = "/company/tasks/" + task["id"]
    first = await client.post(path + "/runs")
    await execute(worker)
    tools = CompanyTools(db, registry=os.registry)
    reviewer = SimpleNamespace(id="reviewer", team_id="review-team")
    ctx = RunContext(run_id="review", session_id="review-session", user_id="alice")
    kwargs = dict(task_id=task["id"], reason="Cite the evidence", _agno_run_context=ctx, _agno_agent=reviewer)
    result = (
        await tools.arequest_company_task_revisions(**kwargs)
        if async_tool
        else await asyncio.to_thread(tools.request_company_task_revisions, **kwargs)
    )
    row = json.loads(result)
    assert row["transitions"][-1]["user_id"] == "reviewer"
    assert row["accepted_by"] == "alice"
    assert row["executor_id"] == "writer"
    started = await client.post(path + "/runs", json={"attempt": 2})
    assert started.status_code == 202, started.text
    job = await worker.store.get_job(started.json()["run_id"])
    value = json.loads(job["payload"]["input"])
    assert value["revision_reasons"] == ["Cite the evidence"]
    assert value["previous_result"]["run_id"] == first.json()["run_id"]


@pytest.mark.asyncio
async def test_templated_namespace_uses_injected_identity(system):
    _, db, _, _, _ = system
    tools = CompanyTools(db, namespace="templated/" + uuid4().hex + "/{user_id}/{agent_id}/{team_id}")
    ctx = RunContext(run_id="review", session_id="session", user_id="alice")
    agent = SimpleNamespace(id="reviewer", team_id="team")
    await tools.alog_company_decision(decision="Keep evidence", _agno_run_context=ctx, _agno_agent=agent)
    result = json.loads(await tools.asearch_company_decisions(_agno_run_context=ctx, _agno_agent=agent))
    assert "Keep evidence" in json.dumps(result)
    ctx.user_id = "bob"
    assert "Keep evidence" not in await tools.asearch_company_decisions(_agno_run_context=ctx, _agno_agent=agent)


@pytest.mark.asyncio
async def test_cancel_then_archive_and_complete_then_archive(system):
    client, _, worker, _, _ = system
    for outcome in ("cancel", "complete"):
        task = await accepted(client)
        path = "/company/tasks/" + task["id"]
        started = await client.post(path + "/runs")
        run_id = started.json()["run_id"]
        refused = await client.delete(path)
        assert refused.status_code == 409 and run_id in refused.text
        if outcome == "cancel":
            assert (await client.post("/company/runs/" + run_id + "/cancel")).status_code == 200
        else:
            await execute(worker)
        assert (await client.delete(path)).status_code == 204


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,identifier", [("agent", "writer"), ("team", "editors"), ("workflow", "draft")])
async def test_plain_component_routes_obey_shared_queue_capacity(system, kind, identifier):
    client, _, worker, _, components = system
    components[identifier].max_concurrent_runs = 1
    first = await client.post(
        f"/{kind}s/{identifier}/runs", data={"message": "First", "background": "true", "stream": "false"}
    )
    assert first.status_code == 202, first.text
    claimed = await worker.store.claim_job("one")
    assert claimed["payload"]["max_concurrent_runs"] == 1
    second = await client.post(
        f"/{kind}s/{identifier}/runs", data={"message": "Second", "background": "true", "stream": "false"}
    )
    assert second.status_code == 202, second.text
    assert await worker.store.claim_job("two") is None
    assert (await worker.store.get_job(second.json()["run_id"]))["status"] == "queued"
    await worker.store.complete_job(claimed["id"], "one", claimed["attempt"], "completed")
    assert (await worker.store.claim_job("two"))["id"] == second.json()["run_id"]
