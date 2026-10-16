"""Task execution through real routes, run storage and a PostgreSQL durable queue."""

import asyncio
import json
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from agno.agent import Agent
from agno.db.base import AsyncBaseDb
from agno.db.postgres import AsyncPostgresDb, PostgresDb
from agno.db.sqlite import AsyncSqliteDb, SqliteDb
from agno.job_queue import QueueConfig
from agno.models.base import Model
from agno.models.message import MessageMetrics
from agno.models.response import ModelResponse
from agno.os import AgentOS, CompanyConfig
from agno.os.job_queue import QueueWorker, resolve_queue_store
from agno.team import Team
from agno.workflow import Step, StepOutput, Workflow


class OfflineModel(Model):
    def __init__(self):
        super().__init__(id="offline", provider="test")

    def invoke(self, *args, **kwargs):
        return ModelResponse(
            role="assistant", content="Completed evidence-based draft", response_usage=MessageMetrics()
        )

    async def ainvoke(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)

    def invoke_stream(self, *args, **kwargs):
        yield self.invoke(*args, **kwargs)

    async def ainvoke_stream(self, *args, **kwargs):
        yield self.invoke(*args, **kwargs)

    def parse_args(self, *args, **kwargs):
        return {}

    def _parse_provider_response(self, response, **kwargs):
        return response

    def _parse_provider_response_delta(self, response):
        return response


def draft(step_input):
    return StepOutput(content="Completed workflow draft")


@pytest_asyncio.fixture(params=["sqlite", "async_sqlite", "postgres", "async_postgres"])
async def system(request, tmp_path):
    schema = "execution_" + uuid4().hex
    queue_db = PostgresDb(db_url="postgresql+psycopg://ai:ai@localhost:5532/ai", db_schema=schema)
    if "postgres" in request.param:
        cls = AsyncPostgresDb if request.param.startswith("async") else PostgresDb
        db = cls(db_url="postgresql+psycopg://ai:ai@localhost:5532/ai", db_schema=schema)
    else:
        cls = AsyncSqliteDb if request.param.startswith("async") else SqliteDb
        db = cls(db_file=str(tmp_path / "company.db"))
    agent = Agent(id="writer", model=OfflineModel(), db=db, telemetry=False)
    team = Team(id="editors", model=OfflineModel(), members=[], db=db, telemetry=False)
    workflow = Workflow(id="draft", steps=[Step(name="Draft", executor=draft)], db=db, telemetry=False)
    config = QueueConfig(durable=True, db=queue_db, max_attempts=2, retry_delay_seconds=0)
    os = AgentOS(
        db=db,
        agents=[agent],
        teams=[team],
        workflows=[workflow],
        company=CompanyConfig(),
        queue=config,
        telemetry=False,
    )
    app = os.get_app()
    components = {"writer": agent, "editors": team, "draft": workflow}
    worker = QueueWorker(
        resolve_queue_store(config, db), lambda kind, id, scope=None: components.get(id), config, authorization_app=app
    )
    worker._company_db = db
    app.state.queue_worker = worker
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, db, worker, os, components
    if isinstance(db, AsyncBaseDb):
        await db.close()
    else:
        db.close()
    with queue_db.db_engine.begin() as conn:
        conn.execute(text('DROP SCHEMA IF EXISTS "' + schema + '" CASCADE'))
    queue_db.close()


async def accepted(client, kind="agent", id="writer"):
    product = (
        await client.post("/company/products", json={"name": "SDK", "metadata": {"secret": "never-forward"}})
    ).json()
    task = (
        await client.post(
            "/company/tasks",
            json={
                "product_id": product["id"],
                "title": "Draft",
                "brief": "Write a draft",
                "evidence": [{"url": "https://example.com/evidence", "hash": "abc"}],
            },
        )
    ).json()
    response = await client.post(
        f"/company/tasks/{task['id']}/transitions",
        json={"target": "ready", "reason": "Approved", "executor_type": kind, "executor_id": id},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def execute(worker):
    job = await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds)
    assert job is not None
    await worker._execute_claimed(job)
    return await worker.store.get_job(job["id"])


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,id", [("agent", "writer"), ("team", "editors"), ("workflow", "draft")])
async def test_execution_duplicate_context_history_and_attention(system, kind, id):
    client, db, worker, os, _ = system
    value = await accepted(client, kind, id)
    path = f"/company/tasks/{value['id']}"
    starts = await asyncio.gather(client.post(path + "/runs"), client.post(path + "/runs"))
    assert all(r.status_code == 202 for r in starts), [r.text for r in starts]
    assert starts[0].json()["run_id"] == starts[1].json()["run_id"]
    run_id = starts[0].json()["run_id"]
    job = await worker.store.get_job(run_id)
    payload = json.loads(job["payload"]["input"])
    assert set(payload) == {"brief", "wiki", "evidence"}
    assert len(payload["wiki"]) == 4 and payload["evidence"][0]["hash"] == "abc"
    assert "never-forward" not in job["payload"]["input"]
    assert job["idempotency_key"] == f"company:{value['id']}:1" and job["max_attempts"] == 2
    assert (await execute(worker))["status"] == "completed"
    saved = (await client.get(path)).json()
    assert saved["status"] == "in_review" and "draft" in saved["result"]["content"]
    assert saved["session_id"] == value["session_id"]
    duplicate = await client.post(path + "/runs")
    assert duplicate.status_code == 202 and duplicate.json()["run_id"] == run_id
    history = (await client.get(path + "/runs", params={"limit": 1, "page": 1})).json()
    assert history["meta"]["total_count"] == 1
    assert (await client.get("/company/attention", params={"product_id": value["product_id"]})).json() == {
        "proposals": 0,
        "in_review": 1,
        "failed": 0,
    }
    assert (await client.post(path + "/runs", json={"attempt": 2})).status_code == 409
    assert (
        await client.post(path + "/transitions", json={"target": "in_progress", "reason": "Revise"})
    ).status_code == 200
    revision = await client.post(path + "/runs", json={"attempt": 2})
    assert revision.status_code == 202, revision.text
    assert revision.json()["session_id"] == value["session_id"] and revision.json()["run_id"] != run_id
    assert (await execute(worker))["status"] == "completed"
    assert (await client.get(path + "/runs", params={"limit": 1, "page": 2})).json()["meta"]["total_count"] == 2


@pytest.mark.asyncio
async def test_cancellation_and_revocation(system):
    client, db, worker, os, _ = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    response = await client.post(path + "/runs")
    assert response.status_code == 202, response.text
    run_id = response.json()["run_id"]
    assert (await client.post(f"/company/runs/{run_id}/cancel")).status_code == 200
    assert (await worker.store.get_job(run_id))["status"] == "cancelled"
    next_run = await client.post(path + "/runs", json={"attempt": 2})
    assert next_run.status_code == 202, next_run.text
    assert (
        await client.post(path + "/transitions", json={"target": "backlog", "reason": "Withdraw"})
    ).status_code == 200
    assert (await execute(worker))["status"] == "failed"
    assert (await client.get(path)).json()["status"] == "backlog"


@pytest.mark.asyncio
async def test_registry_recheck_and_engineering(system):
    client, db, worker, os, _ = system
    value = await accepted(client)
    os.registry.agents.clear()
    assert (await client.post(f"/company/tasks/{value['id']}/runs")).status_code == 409
    engineering = await accepted(client, "engineering", "codex")
    response = await client.post(f"/company/tasks/{engineering['id']}/runs")
    assert response.status_code == 409 and "Engineering" in response.text


@pytest.mark.asyncio
async def test_bounded_failure_visible_without_changing_lifecycle(system, monkeypatch):
    client, db, worker, os, components = system
    value = await accepted(client)

    async def fail(*args, **kwargs):
        raise RuntimeError("executor failed")

    monkeypatch.setattr(components["writer"], "arun", fail)
    path = f"/company/tasks/{value['id']}"
    assert (await client.post(path + "/runs")).status_code == 202
    first = await execute(worker)
    assert first["status"] == "queued"
    pending = (await client.get(path)).json()
    assert pending["status"] == "in_progress" and pending["result"] is None
    assert (await client.get("/company/attention")).json()["failed"] == 0
    assert (await client.get("/company/tasks", params={"failed": "true"})).json()["meta"]["total_count"] == 0
    second = await execute(worker)
    assert second["status"] == "failed" and second["attempt"] == 2
    saved = (await client.get(path)).json()
    assert saved["status"] == "in_progress" and saved["result"]["status"] == "ERROR"
    assert (await client.get("/company/attention")).json()["failed"] == 1
    rows = (await client.get("/company/tasks", params={"failed": "true"})).json()
    assert rows["meta"]["total_count"] == 1 and rows["data"][0]["id"] == value["id"]


@pytest.mark.asyncio
async def test_queue_reconciliation_projects_completion_after_restart(system, monkeypatch):
    client, db, worker, os, components = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    assert (await client.post(path + "/runs")).status_code == 202

    async def lost_settlement(*args, **kwargs):
        return False

    monkeypatch.setattr(worker, "_asettle_ticket", lost_settlement)
    first = await execute(worker)
    assert first["status"] == "running"
    assert (await client.get(path)).json()["status"] == "in_progress"
    # Reclaim by a new worker after a lost lease; it must honor the terminal run row.
    restarted = QueueWorker(
        worker.store, worker.resolve_component, worker.config, authorization_app=worker.authorization_app
    )
    restarted._company_db = db
    queue_db = worker.config.db
    table = queue_db._get_table("jobs")
    with queue_db.Session() as session, session.begin():
        session.execute(table.update().where(table.c.id == first["id"]).values(locked_at=0))
    assert (await execute(restarted))["status"] == "completed"
    assert (await client.get(path)).json()["status"] == "in_review"
    assert (await client.get(path + "/runs")).json()["meta"]["total_count"] == 1


@pytest.mark.asyncio
async def test_custom_task_table_is_created_with_execution_fields(system):
    from sqlalchemy import inspect

    from agno.company.execution import _call

    client, db, worker, os, _ = system
    name = "custom_company_tasks"
    db.tasks_table_name = name
    value = await accepted(client)
    saved = await _call(db, "get_task", value["id"])
    assert saved["session_id"]
    assert saved["job_id"] is None and saved["result"] is None
    assert saved["evidence"] == [{"url": "https://example.com/evidence", "hash": "abc"}]

    def inspect_table(conn):
        inspector = inspect(conn)
        schema = getattr(db, "db_schema", None)
        return inspector.get_columns(name, schema=schema), inspector.get_indexes(name, schema=schema)

    if isinstance(db, AsyncBaseDb):
        async with db.db_engine.connect() as conn:
            columns, indexes = await conn.run_sync(inspect_table)
    else:
        with db.db_engine.connect() as conn:
            columns, indexes = inspect_table(conn)
    assert {"session_id", "job_id", "evidence", "result"} <= {column["name"] for column in columns}
    assert {f"idx_{name}_session_id", f"idx_{name}_job_id"} <= {index["name"] for index in indexes}

    response = await client.post(f"/company/tasks/{value['id']}/runs")
    assert response.status_code == 202, response.text
    assert (await execute(worker))["status"] == "completed"
    assert (await client.get(f"/company/tasks/{value['id']}")).json()["status"] == "in_review"


@pytest.mark.asyncio
async def test_results_cannot_cross_revoked_acceptance(system):
    from agno.company.execution import _call
    from agno.db.schemas.tasks import task_run_id

    client, db, worker, os, _ = system
    value = await accepted(client)
    reserved = await _call(db, "start_task_run", value["id"], 1, value["transitions"])
    await _call(db, "transition_task", value["id"], "backlog", "Withdraw")
    await _call(db, "transition_task", value["id"], "ready", "New scope", executor_type="agent", executor_id="writer")
    await _call(db, "transition_task", value["id"], "in_progress", "Manual work")
    assert (
        await _call(
            db,
            "complete_task_run",
            value["id"],
            task_run_id(value["id"], 1),
            {"status": "COMPLETED", "content": "stale"},
            expected_transitions=reserved["transitions"],
        )
        is None
    )
    saved = await _call(db, "get_task", value["id"])
    assert saved["status"] == "in_progress" and saved["result"] is None


@pytest.mark.asyncio
async def test_run_history_and_duplicate_survive_ticket_retention(system):
    client, db, worker, os, _ = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    response = await client.post(path + "/runs")
    run_id = response.json()["run_id"]
    assert (await execute(worker))["status"] == "completed"
    table = worker.config.db._get_table("jobs")
    with worker.config.db.Session() as session, session.begin():
        session.execute(table.delete().where(table.c.id == run_id))
    assert (await client.post(path + "/runs")).json()["run_id"] == run_id
    response = await client.get(f"/company/runs/{run_id}")
    assert response.status_code == 200 and response.json()["status"] == "COMPLETED", response.text
    assert (
        await client.post(path + "/transitions", json={"target": "in_progress", "reason": "Revise draft"})
    ).status_code == 200
    revision = await client.post(path + "/runs", json={"attempt": 2})
    assert revision.status_code == 202, revision.text
    assert revision.json()["run_id"] != run_id
    os.registry.agents.clear()
    assert (await client.get(path + "/runs")).json()["meta"]["total_count"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,id", [("agent", "writer"), ("team", "editors"), ("workflow", "draft")])
async def test_invalid_executor_input_does_not_reserve_attempt(system, kind, id):
    from pydantic import BaseModel

    from agno.db.schemas.tasks import task_run_id

    class TopicInput(BaseModel):
        topic: str

    client, db, worker, os, components = system
    component = components[id]
    component.input_schema = TopicInput
    value = await accepted(client, kind, id)
    path = f"/company/tasks/{value['id']}"
    response = await client.post(path + "/runs")
    assert response.status_code == 400, response.text
    saved = (await client.get(path)).json()
    assert saved["status"] == "ready"
    assert saved["job_id"] is None
    assert saved["transitions"] == value["transitions"]
    assert await worker.store.get_job(task_run_id(value["id"], 1)) is None
    assert (await client.get(path + "/runs")).json()["meta"]["total_count"] == 0

    # A rejected input has not consumed the attempt. Correcting the executor's
    # schema permits the same first attempt to enter the ordinary durable route.
    component.input_schema = None
    retried = await client.post(path + "/runs")
    assert retried.status_code == 202, retried.text
    assert (await execute(worker))["status"] == "completed"


@pytest.mark.asyncio
async def test_nonfailed_filter_includes_sql_and_json_null_results(system):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    unstarted = await accepted(client)
    pending = await accepted(client)
    response = await client.post(f"/company/tasks/{pending['id']}/runs")
    assert response.status_code == 202, response.text
    nonfailed = (await client.get("/company/tasks", params={"failed": "false", "limit": 1})).json()
    assert nonfailed["meta"]["total_count"] == 2
    assert len(nonfailed["data"]) == 1
    assert (await client.get("/company/tasks", params={"failed": "true"})).json()["meta"]["total_count"] == 0

    await _call(
        db, "complete_task_run", pending["id"], response.json()["run_id"], {"status": "ERROR", "content": "Failure"}
    )
    nonfailed = (await client.get("/company/tasks", params={"failed": "false"})).json()
    failed = (await client.get("/company/tasks", params={"failed": "true"})).json()
    assert nonfailed["meta"]["total_count"] == 1
    assert [row["id"] for row in nonfailed["data"]] == [unstarted["id"]]
    assert failed["meta"]["total_count"] == 1
    assert [row["id"] for row in failed["data"]] == [pending["id"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["cancelled", "backlog", "ready", "in_review", "done"])
@pytest.mark.parametrize("result_status", ["ERROR", "CANCELLED"])
async def test_attention_clears_acted_on_failures_and_preserves_results(system, target, result_status):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    value = await accepted(client)
    other = await accepted(client)
    for task in (value, other):
        reserved = await _call(db, "start_task_run", task["id"], 1, task["transitions"])
        await _call(
            db, "complete_task_run", task["id"], reserved["job_id"], {"status": result_status, "content": "Failure"}
        )
    path = f"/company/tasks/{value['id']}"
    product_filter = {"product_id": value["product_id"]}
    assert (await client.get("/company/attention", params=product_filter)).json()["failed"] == 1
    assert (await client.get("/company/attention")).json()["failed"] == 2
    steps = ["backlog", "ready"] if target == "ready" else ["in_review", "done"] if target == "done" else [target]
    for step in steps:
        body = {"target": step, "reason": "Human acted on failure"}
        if step == "ready":
            body.update(executor_type="agent", executor_id="writer")
        response = await client.post(path + "/transitions", json=body)
        assert response.status_code == 200, response.text
        attention = (await client.get("/company/attention", params=product_filter)).json()
        assert attention == {"proposals": int(step == "backlog"), "in_review": int(step == "in_review"), "failed": 0}
    assert (await client.get(path)).json()["result"] == {"status": result_status, "content": "Failure"}
    assert (await client.get("/company/attention")).json()["failed"] == 1
    failed = (await client.get("/company/tasks", params={"failed": "true", "limit": 1})).json()
    nonfailed = (await client.get("/company/tasks", params={"failed": "false", "limit": 1})).json()
    assert failed["meta"]["total_count"] == nonfailed["meta"]["total_count"] == 1
    assert [row["id"] for row in failed["data"]] == [other["id"]]
    assert [row["id"] for row in nonfailed["data"]] == [value["id"]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,executor_id",
    [
        ("agent", "product-manager-internal"),
        ("team", "os-manager-internal"),
        ("agent", "platform-builder-internal"),
        ("agent", "platform-manager-internal"),
    ],
)
@pytest.mark.parametrize("phase", ["acceptance", "start"])
async def test_all_framework_executor_ids_are_rejected(system, monkeypatch, kind, executor_id, phase):
    from unittest.mock import Mock

    from agno.company.execution import _call

    client, db, worker, os, components = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    await _call(db, "transition_task", value["id"], "backlog", "Replan")
    # The Company boundary must reject reserved IDs even if a custom registry
    # resolver returns a component, rather than relying on catalog exclusion.
    resolve = Mock(return_value=components["writer" if kind == "agent" else "editors"])
    monkeypatch.setattr(os.registry, "get_" + kind, resolve)
    if phase == "acceptance":
        response = await client.post(
            path + "/transitions",
            json={"target": "ready", "reason": "Accept", "executor_type": kind, "executor_id": executor_id},
        )
        assert response.status_code == 409, response.text
        assert (await client.get(path)).json()["status"] == "backlog"
    else:
        await _call(
            db,
            "transition_task",
            value["id"],
            "ready",
            "Previously accepted",
            executor_type=kind,
            executor_id=executor_id,
        )
        response = await client.post(path + "/runs")
        assert response.status_code == 409, response.text
        assert (await client.get(path)).json()["job_id"] is None
    resolve.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,id", [("agent", "writer"), ("team", "editors"), ("workflow", "draft")])
@pytest.mark.parametrize("attempt", [1, 2])
async def test_full_queue_leaves_task_and_attempt_unchanged(system, kind, id, attempt):
    from agno.company.execution import _call
    from agno.db.schemas.tasks import task_run_id

    client, db, worker, os, _ = system
    value = await accepted(client, kind, id)
    path = f"/company/tasks/{value['id']}"
    if attempt == 2:
        response = await client.post(path + "/runs")
        job = await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds)
        assert job["id"] == response.json()["run_id"]
        await _call(db, "complete_task_run", value["id"], job["id"], {"status": "ERROR", "content": "Previous failure"})
        assert await worker.store.complete_job(job["id"], worker.worker_id, job["attempt"], "failed")
    filler = await accepted(client)
    filler_run = await client.post(f"/company/tasks/{filler['id']}/runs")
    worker.config.max_queue_depth = 1
    before = (await client.get(path)).json()
    attention = (await client.get("/company/attention")).json()
    for _ in range(2):
        response = await client.post(path + "/runs", json={"attempt": attempt})
        assert response.status_code == 429, response.text
        assert (await client.get(path)).json() == before
        assert await worker.store.get_job(task_run_id(value["id"], attempt)) is None
        assert (await client.get(path + "/runs")).json()["meta"]["total_count"] == attempt - 1
        assert (await client.get("/company/attention")).json() == attention
    assert (await client.post(f"/company/runs/{filler_run.json()['run_id']}/cancel")).status_code == 200
    retried = await client.post(path + "/runs", json={"attempt": attempt})
    assert retried.status_code == 202, retried.text
    assert (await execute(worker))["status"] == "completed"
    assert (await client.get(path)).json()["status"] == "in_review"


@pytest.mark.asyncio
async def test_rejected_duplicate_cannot_undo_accepted_submission(system, monkeypatch):
    client, db, worker, os, _ = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    filler = await accepted(client)
    filler_run = await client.post(f"/company/tasks/{filler['id']}/runs")
    worker.config.max_queue_depth = 1
    enqueue = worker.store.enqueue_job
    rejected = asyncio.Event()
    release = asyncio.Event()

    async def delayed_rejection(*args, **kwargs):
        result = await enqueue(*args, **kwargs)
        if result["reason"] == "queue_full":
            rejected.set()
            await release.wait()
        return result

    monkeypatch.setattr(worker.store, "enqueue_job", delayed_rejection)
    first = asyncio.create_task(client.post(path + "/runs"))
    try:
        await asyncio.wait_for(rejected.wait(), timeout=10)
        assert (await client.post(f"/company/runs/{filler_run.json()['run_id']}/cancel")).status_code == 200
        second = await client.post(path + "/runs")
        assert second.status_code == 202, second.text
    finally:
        release.set()
    assert (await first).status_code == 429
    saved = (await client.get(path)).json()
    assert saved["status"] == "in_progress" and saved["job_id"] == second.json()["run_id"]
    assert (await execute(worker))["status"] == "completed"
    assert (await client.get(path)).json()["status"] == "in_review"


@pytest.mark.asyncio
@pytest.mark.parametrize("recovery", ["worker", "duplicate", "cancel", "revoke"])
async def test_worker_recovers_task_projection_after_committed_enqueue(system, monkeypatch, recovery):
    import agno.company.execution as execution
    from agno.db.schemas.tasks import task_run_id

    client, db, worker, os, _ = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    reserve = execution._reserve_task

    async def lost_submitter(*args, **kwargs):
        raise RuntimeError("Submitter stopped after enqueue")

    monkeypatch.setattr(execution, "_reserve_task", lost_submitter)
    with pytest.raises(RuntimeError, match="Submitter stopped after enqueue"):
        await client.post(path + "/runs")
    assert (await client.get(path)).json() == value
    assert await worker.store.get_job(task_run_id(value["id"], 1)) is not None
    monkeypatch.setattr(execution, "_reserve_task", reserve)
    if recovery == "duplicate":
        assert (await client.post(path + "/runs")).status_code == 202
        assert (await client.get(path)).json()["status"] == "in_progress"
    elif recovery == "cancel":
        run_id = task_run_id(value["id"], 1)
        assert (await client.post(f"/company/runs/{run_id}/cancel")).status_code == 200
        assert (await client.post(path + "/runs", json={"attempt": 2})).status_code == 202
    elif recovery == "revoke":
        assert (
            await client.post(path + "/transitions", json={"target": "backlog", "reason": "Withdraw"})
        ).status_code == 200
    result = await execute(worker)
    saved = (await client.get(path)).json()
    assert result["status"] == ("failed" if recovery == "revoke" else "completed")
    assert saved["status"] == ("backlog" if recovery == "revoke" else "in_review")
    if recovery == "revoke":
        assert saved["job_id"] is None and saved["result"] is None
    else:
        assert saved["result"]["status"] == "COMPLETED"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,id", [("agent", "writer"), ("team", "editors"), ("workflow", "draft")])
async def test_cancelled_task_is_visible_and_can_start_another_attempt(system, kind, id):
    from agno.company.execution import _project_run

    client, db, worker, os, _ = system
    value = await accepted(client, kind, id)
    path = f"/company/tasks/{value['id']}"
    response = await client.post(path + "/runs")
    run_id = response.json()["run_id"]
    job = await worker.store.get_job(run_id)
    assert (await client.post(f"/company/runs/{run_id}/cancel")).status_code == 200
    assert (await worker.store.get_job(run_id))["status"] == "cancelled"
    saved = (await client.get(path)).json()
    assert saved["status"] == "in_progress"
    assert saved["result"]["status"] == "CANCELLED" and saved["result"]["run_id"] == run_id
    assert saved["result"]["content"]
    assert (await client.get("/company/attention", params={"product_id": value["product_id"]})).json()["failed"] == 1
    assert (await client.get("/company/tasks", params={"failed": True})).json()["meta"]["total_count"] == 1
    assert (await client.get("/company/tasks", params={"failed": False})).json()["meta"]["total_count"] == 0
    assert (await client.get(path + "/runs")).json()["data"][0]["status"] == "CANCELLED"

    response = await client.post(path + "/runs", json={"attempt": 2})
    assert response.status_code == 202, response.text
    pending = (await client.get(path)).json()
    assert pending["session_id"] == value["session_id"] and pending["result"] is None
    await _project_run(worker, job, "cancelled")
    assert (await client.get(path)).json() == pending
    assert (await client.get("/company/attention")).json()["failed"] == 0
    assert (await execute(worker))["status"] == "completed"


@pytest.mark.asyncio
async def test_cancellation_during_execution_projects_task_result(system, monkeypatch):
    from agno.exceptions import RunCancelledException

    client, db, worker, os, components = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    response = await client.post(path + "/runs")
    run_id = response.json()["run_id"]
    started = asyncio.Event()
    release = asyncio.Event()

    async def cancelled_run(*args, **kwargs):
        started.set()
        await release.wait()
        raise RunCancelledException("User cancelled execution")

    monkeypatch.setattr(components["writer"], "arun", cancelled_run)
    running = asyncio.create_task(execute(worker))
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        assert (await client.post(f"/company/runs/{run_id}/cancel")).status_code == 200
    finally:
        release.set()
    assert (await running)["status"] == "cancelled"
    saved = (await client.get(path)).json()
    assert saved["status"] == "in_progress" and saved["result"]["status"] == "CANCELLED"
    assert (await client.get("/company/attention")).json()["failed"] == 1
    assert (await client.post(path + "/transitions", json={"target": "backlog", "reason": "Replan"})).status_code == 200
    assert (await client.get("/company/attention")).json() == {"proposals": 1, "in_review": 0, "failed": 0}
    assert (await client.get(path)).json()["result"]["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_projection_failure_is_recovered_by_queue(system, monkeypatch):
    import agno.company.execution as execution

    client, db, worker, os, _ = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    response = await client.post(path + "/runs")
    run_id = response.json()["run_id"]
    project = execution._project_run

    async def interrupted(*args, **kwargs):
        raise RuntimeError("Task projection interrupted")

    monkeypatch.setattr(execution, "_project_run", interrupted)
    with pytest.raises(RuntimeError, match="Task projection interrupted"):
        await client.post(f"/company/runs/{run_id}/cancel")
    assert (await worker.store.get_job(run_id))["status"] == "queued"
    assert (await client.get(path)).json()["result"] is None
    monkeypatch.setattr(execution, "_project_run", project)
    assert (await execute(worker))["status"] == "cancelled"
    assert (await client.get(path)).json()["result"]["status"] == "CANCELLED"
    assert (await client.get("/company/attention")).json()["failed"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("claimed", [False, True], ids=["queued", "claimed"])
async def test_changed_acceptance_during_enqueue_returns_conflict(system, monkeypatch, claimed):
    from agno.db.schemas.tasks import task_run_id

    client, db, worker, os, components = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    enqueue = worker.store.enqueue_job
    claimed_job = None

    async def revoke_before_enqueue(*args, **kwargs):
        nonlocal claimed_job
        revoked = await client.post(path + "/transitions", json={"target": "backlog", "reason": "Scope changed"})
        assert revoked.status_code == 200
        result = await enqueue(*args, **kwargs)
        if claimed:
            claimed_job = await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds)
        return result

    monkeypatch.setattr(worker.store, "enqueue_job", revoke_before_enqueue)
    response = await client.post(path + "/runs")
    assert response.status_code == 409, response.text
    assert "acceptance" in response.json()["detail"]
    saved = (await client.get(path)).json()
    assert saved["status"] == "backlog" and saved["job_id"] is None and saved["result"] is None
    run_id = task_run_id(value["id"], 1)
    if claimed:
        from unittest.mock import AsyncMock

        run = AsyncMock(side_effect=AssertionError("Revoked work must never execute"))
        monkeypatch.setattr(components["writer"], "arun", run)
        await worker._execute_claimed(claimed_job)
        run.assert_not_awaited()
    job = await worker.store.get_job(run_id)
    assert job["status"] == ("failed" if claimed else "cancelled")
    assert (await client.get(path)).json() == saved
    assert (await client.get("/company/attention")).json() == {"proposals": 1, "in_review": 0, "failed": 0}


@pytest.mark.asyncio
async def test_worker_completion_before_submitter_reservation_still_returns_accepted(system, monkeypatch):
    client, db, worker, os, _ = system
    value = await accepted(client)
    path = f"/company/tasks/{value['id']}"
    enqueue = worker.store.enqueue_job

    async def complete_before_submitter_returns(*args, **kwargs):
        result = await enqueue(*args, **kwargs)
        assert (await execute(worker))["status"] == "completed"
        return result

    monkeypatch.setattr(worker.store, "enqueue_job", complete_before_submitter_returns)
    response = await client.post(path + "/runs")
    assert response.status_code == 202, response.text
    saved = (await client.get(path)).json()
    assert saved["status"] == "in_review" and saved["result"]["status"] == "COMPLETED"
    assert (await worker.store.get_job(response.json()["run_id"]))["status"] == "completed"
