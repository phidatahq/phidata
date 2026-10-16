"""Execution gates, shared reads and existing run ownership rules."""

import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.company import CompanyManager
from agno.company.execution import _ExecutorAuthorization
from agno.db.sqlite import SqliteDb
from agno.job_queue import QueueConfig
from agno.job_queue.store import InMemoryQueueStore
from agno.os import AgentOS, CompanyConfig
from agno.os.authz import Authorization
from agno.os.job_queue import QueueWorker
from agno.registry import Registry
from agno.tools.scheduler import SchedulerTools

SECRET = "company-execution-tests-secret-at-least-32-bytes"
SCOPES = ["products:read", "products:write", "tasks:read", "tasks:write", "wiki:read", "agents:writer:run"]


def headers(user="alice", scopes=None):
    return {
        "Authorization": "Bearer "
        + jwt.encode(
            {
                "sub": user,
                "aud": "company-execution",
                "scopes": SCOPES if scopes is None else scopes,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            SECRET,
            algorithm="HS256",
        )
    }


@pytest.fixture(params=[False, True], ids=["shared", "isolated"])
def system(request, tmp_path):
    db = SqliteDb(db_file=str(tmp_path / "company.db"))
    writer = Agent(id="writer", db=db)
    os = AgentOS(
        id="company-execution",
        db=db,
        registry=Registry(agents=[writer]),
        company=CompanyConfig(),
        telemetry=False,
        user_isolation=request.param,
        authorization=Authorization(verification_keys=[SECRET], algorithm="HS256"),
    )
    app = os.get_app()
    config = QueueConfig(durable=True)
    queue = QueueWorker(InMemoryQueueStore(), lambda *a, **k: writer, config, authorization_app=app)
    queue._company_db = db
    app.state.queue_worker = queue
    yield TestClient(app), db, os, queue
    db.close()


def accepted(client):
    product = client.post("/company/products", json={"name": "SDK"}, headers=headers()).json()
    task = client.post(
        "/company/tasks", json={"product_id": product["id"], "title": "Draft", "brief": "Write"}, headers=headers()
    ).json()
    path = f"/company/tasks/{task['id']}"
    response = client.post(
        path + "/transitions",
        json={"target": "ready", "reason": "Approved", "executor_type": "agent", "executor_id": "writer"},
        headers=headers(),
    )
    assert response.status_code == 200, response.text
    return path, response.json()


def test_missing_executor_at_acceptance_and_registry_only_mount(system):
    client, db, os, queue = system
    path, task = accepted(client)
    assert client.post(path + "/runs", headers=headers()).status_code == 202
    other = client.post(
        "/company/tasks", json={"product_id": task["product_id"], "title": "Other"}, headers=headers()
    ).json()
    denied = client.post(
        f"/company/tasks/{other['id']}/transitions",
        json={"target": "ready", "reason": "Approved", "executor_type": "agent", "executor_id": "missing"},
        headers=headers(scopes=["agent_os:admin"]),
    )
    assert denied.status_code == 409
    assert client.get(f"/company/tasks/{other['id']}", headers=headers()).json()["status"] == "backlog"


def test_start_requires_current_run_and_wiki_permissions(system):
    client, db, os, queue = system
    path, task = accepted(client)
    for omitted in ("agents:writer:run", "wiki:read", "tasks:write"):
        response = client.post(path + "/runs", headers=headers(scopes=[scope for scope in SCOPES if scope != omitted]))
        assert response.status_code == 403, response.text
    assert client.get(path, headers=headers()).json()["status"] == "ready"
    os.registry.agents.clear()
    assert client.post(path + "/runs", headers=headers()).status_code == 409


def test_attention_history_and_duplicates_are_shared(system):
    client, db, os, queue = system
    path, task = accepted(client)
    start = client.post(path + "/runs", headers=headers())
    assert start.status_code == 202, start.text
    duplicate = client.post(path + "/runs", headers=headers("bob"))
    assert duplicate.status_code == 202 and duplicate.json()["run_id"] == start.json()["run_id"]
    assert client.get(path + "/runs", headers=headers("bob")).json()["meta"]["total_count"] == 1
    assert client.get("/company/attention", headers=headers("bob")).status_code == 200
    assert client.get("/company/attention", headers=headers(scopes=[])).status_code == 403
    cancelled = client.post(f"/company/runs/{start.json()['run_id']}/cancel", headers=headers())
    assert cancelled.status_code == 200, cancelled.text


def test_unaccepted_no_queue_and_request_overrides(system):
    client, db, os, queue = system
    path, task = accepted(client)
    assert (
        client.post(path + "/runs", json={"message": "smuggle", "session_id": "foreign"}, headers=headers()).status_code
        == 422
    )
    client.app.state.queue_worker = None
    assert client.post(path + "/runs", headers=headers()).status_code == 503
    assert client.get(path, headers=headers()).json()["status"] == "ready"


def test_python_acceptance_also_validates_registry(tmp_path):
    db = SqliteDb(db_file=str(tmp_path / "registry.db"))
    manager = CompanyManager(db)
    product = manager.create("SDK")
    task = manager.create_task(product["id"], "Draft")
    with pytest.raises(ValueError, match="missing"):
        manager.transition_task(task["id"], "ready", "Accept", executor_type="agent", executor_id="writer")
    manager.registry = Registry(agents=[Agent(id="writer", tools=[SchedulerTools(db=db)])])
    with pytest.raises(ValueError, match="SchedulerTools"):
        manager.transition_task(task["id"], "ready", "Accept", executor_type="agent", executor_id="writer")
    db.close()


def test_company_executor_cannot_acquire_schedule_mutation_authority():
    authority = _ExecutorAuthorization(None)
    for action in ("write", "delete"):
        with pytest.raises(PermissionError, match="schedules"):
            authority.require("schedules", action)
        with pytest.raises(PermissionError, match="schedules"):
            asyncio.run(authority.arequire("schedules", action))
    authority.require("schedules", "read")


def test_run_routes_without_company_database():
    app = AgentOS(company=CompanyConfig(), telemetry=False).get_app()
    with TestClient(app) as client:
        assert client.get("/company/runs/missing").status_code == 503
        assert client.post("/company/runs/missing/cancel").status_code == 503


def test_missing_product_context_does_not_reserve_execution(system):
    client, db, os, queue = system
    path, task = accepted(client)
    assert db.delete_product(task["product_id"])
    response = client.post(path + "/runs", headers=headers())
    assert response.status_code == 404, response.text
    assert db.get_task(task["id"])["job_id"] is None


@pytest.mark.parametrize(
    "resource,executor_id",
    [
        ("agents", "product-manager-internal"),
        ("teams", "os-manager-internal"),
        ("agents", "platform-builder-internal"),
        ("agents", "platform-manager-internal"),
    ],
)
def test_registry_mount_excludes_all_framework_executors(resource, executor_id):
    from types import SimpleNamespace

    from agno.company.execution import _mount_executors

    ordinary = SimpleNamespace(id="ordinary")
    reserved = SimpleNamespace(id=executor_id)
    registry = SimpleNamespace(agents=[], teams=[], workflows=[])
    setattr(registry, resource, [ordinary, reserved])
    os = SimpleNamespace(registry=registry, agents=[], teams=[], workflows=[])
    _mount_executors(os)
    assert getattr(os, resource) == [ordinary]


def test_simultaneous_collaborators_share_committed_run(system, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    client, db, os, queue = system
    path, value = accepted(client)
    enqueue = queue.store.enqueue_job

    async def concurrent_starts():
        arrivals = 0
        both_arrived = asyncio.Event()

        async def simultaneous_enqueue(*args, **kwargs):
            nonlocal arrivals
            arrivals += 1
            if arrivals == 2:
                both_arrived.set()
            await asyncio.wait_for(both_arrived.wait(), timeout=10)
            return await enqueue(*args, **kwargs)

        monkeypatch.setattr(queue.store, "enqueue_job", simultaneous_enqueue)
        async with AsyncClient(transport=ASGITransport(app=client.app), base_url="http://test") as async_client:
            return await asyncio.gather(
                async_client.post(path + "/runs", headers=headers("alice")),
                async_client.post(path + "/runs", headers=headers("bob")),
            )

    responses = asyncio.run(concurrent_starts())
    assert all(response.status_code == 202 for response in responses), [response.text for response in responses]
    assert responses[0].json()["run_id"] == responses[1].json()["run_id"]
    saved = db.get_task(value["id"])
    assert saved["status"] == "in_progress"
    assert len([entry for entry in saved["transitions"] if entry.get("attempt") == 1]) == 1
