"""Task execution through real routes, run storage and a PostgreSQL durable queue."""

import asyncio
import json
import time
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
    assert {"session_id", "job_id", "evidence", "result", "origin", "routine_id", "dedupe_key"} <= {
        column["name"] for column in columns
    }
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
    reserved = await _call(
        db, "start_task_run", value["id"], 1, (await _call(db, "get_task", value["id"]))["transitions"]
    )
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
@pytest.mark.parametrize("failure", [None, "missing", "markdown", "website", "git", "plain_proposal"])
async def test_routine_intake_through_scheduler_and_durable_queue(system, tmp_path, monkeypatch, failure):
    from agno.company.execution import _call
    from agno.scheduler.executor import ScheduleExecutor
    from agno.tools.company import CompanyTools

    client, db, worker, os, components = system
    path = tmp_path / "release.md"
    path.write_text("A released capability")
    product = (await client.post("/company/products", json={"name": "Docs"})).json()
    source = (
        await client.post(
            "/company/sources", json={"product_id": product["id"], "type": "markdown", "reference": str(path)}
        )
    ).json()

    if failure == "missing":
        path.unlink()
    elif failure == "markdown":

        def broken_reader(*args, **kwargs):
            raise OSError("Reader backend failed")

        monkeypatch.setattr("agno.knowledge.reader.markdown_reader.MarkdownReader.read", broken_reader)
    elif failure == "git":
        (tmp_path / ".env").write_text("Excluded from the Source")
        await _call(db, "update_source", source["id"], type="git", reference=str(tmp_path), config={"paths": [".env"]})
    elif failure == "website":
        await _call(db, "update_source", source["id"], type="website", reference="https://docs.example.test")
        monkeypatch.setattr("agno.knowledge.reader.website_reader.WebsiteReader.read", lambda *args, **kwargs: [])
    tool_name = "read_company_source" if failure in {"markdown", "website"} else "intake_company_source"
    arguments = {"source_id": source["id"]}
    if failure == "plain_proposal":
        tool_name = "propose_company_task"
        arguments = {"product_id": product["id"], "title": "Undeduplicated proposal"}
    if tool_name == "read_company_source":
        arguments["path"] = "https://docs.example.test" if failure == "website" else path.name
    if tool_name == "intake_company_source":
        arguments.update(
            title="Document release",
            brief="Explain the capability",
            proposal_key="release-docs",
            evidence_links=[path.as_uri()],
            evidence_hashes={path.as_uri(): "unavailable"},
        )

    if failure is None:
        from agno.company.sources import read_source

        evidence = read_source(source, "observed")
        arguments["evidence_hashes"] = {item["link"]: item["content_hash"] for item in evidence}

    class IntakeModel(OfflineModel):
        def invoke(self, messages, *args, **kwargs):
            assert any(product["id"] in str(message.content) for message in messages if message.role == "user")
            if not any(message.role == "tool" for message in messages):
                return ModelResponse(
                    role="assistant",
                    tool_calls=[
                        {
                            "id": "intake",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                    response_usage=MessageMetrics(),
                )
            return ModelResponse(
                role="assistant",
                content="Source checked; proposals remain in Backlog.",
                response_usage=MessageMetrics(),
            )

    components["writer"].model = IntakeModel()
    components["writer"].tools = [CompanyTools(db)]
    os.resync(worker.authorization_app)
    response = await client.post(
        "/company/routines",
        json={
            "product_id": product["id"],
            "name": "intake",
            "template": "intake",
            "executor_type": "agent",
            "executor_id": "writer",
            "cron_expr": "0 * * * *",
        },
    )
    assert response.status_code == 201, response.text
    routine = response.json()
    app = worker.authorization_app
    app.state.internal_service_token = "heartbeat-internal"
    executor = ScheduleExecutor(base_url="http://test", internal_service_token="heartbeat-internal", poll_interval=0)
    original_request = client.request

    async def request_and_work(method, url, **kwargs):
        result = await original_request(method, url, **kwargs)
        if method == "POST" and result.status_code == 202:
            completed = await execute(worker)
            if failure and completed["status"] == "queued":
                completed = await execute(worker)
            assert completed["status"] == ("failed" if failure else "completed"), completed
        return result

    from unittest.mock import AsyncMock

    executor._get_client = AsyncMock(return_value=SimpleClient(request_and_work))
    schedule = await _call(db, "get_schedule", routine["id"])
    first = await executor.execute(schedule, db, release_schedule=False)
    if failure:
        assert first["status"] == "failed", first
        assert tool_name in first["error"]
        assert (await _call(db, "get_tasks", product_id=product["id"]))[1] == 0
        history = (await client.get("/company/routines/" + routine["id"] + "/runs")).json()
        assert history["data"][0]["status"] == "failed"
        assert (await client.get("/company/attention", params={"product_id": product["id"]})).json()["failed"] == 1
        run = await components["writer"].aget_run_output(first["run_id"], first["session_id"])
        assert str(run.status).upper() == "ERROR"
        return
    assert first["status"] == "success", first
    rows, total = await _call(db, "get_tasks", product_id=product["id"])
    assert total == 1, first
    assert rows[0]["routine_id"] == routine["id"]
    task_response = (await client.get("/company/tasks/" + rows[0]["id"])).json()
    assert task_response["origin"] == "routine"
    assert task_response["routine_id"] == routine["id"]
    assert task_response["dedupe_key"] == rows[0]["dedupe_key"]
    assert rows[0]["evidence"][0]["run_id"] == first["run_id"]
    assert rows[0]["status"] == "backlog"
    second = await executor.execute(schedule, db, release_schedule=False)
    assert second["status"] == "success", second
    assert (await _call(db, "get_tasks", product_id=product["id"]))[1] == 1
    history = (await client.get("/company/routines/" + routine["id"] + "/runs")).json()
    assert history["meta"]["total_count"] == 2
    assert all(run["status"] == "success" for run in history["data"])


class SimpleClient:
    def __init__(self, request):
        self.request = request


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
        reserved = await _call(
            db, "start_task_run", task["id"], 1, (await _call(db, "get_task", task["id"]))["transitions"]
        )
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
@pytest.mark.parametrize("recovery", ["worker", "duplicate", "cancel", "revoke", "archive_restore"])
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
    elif recovery == "archive_restore":
        assert (await client.delete(path)).status_code == 204
        restored = await client.post(path + "/restore")
        assert restored.status_code == 200, restored.text
        assert restored.json()["transitions"] == value["transitions"]
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


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["queued", "running", "revoked"])
async def test_task_archive_restore_preserves_queued_acceptance(system, monkeypatch, phase):
    client, db, worker, os, components = system
    task = await accepted(client)
    path = "/company/tasks/" + task["id"]
    started = await client.post(path + "/runs")
    assert started.status_code == 202, started.text
    run_id = started.json()["run_id"]
    before = (await client.get(path)).json()
    entered, release = asyncio.Event(), asyncio.Event()
    original = components["writer"].arun

    async def paused(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    running = None
    if phase == "running":
        monkeypatch.setattr(components["writer"], "arun", paused)
        running = asyncio.create_task(execute(worker))
    try:
        if running is not None:
            await asyncio.wait_for(entered.wait(), timeout=10)
        assert (await client.delete(path)).status_code == 204
        restored = await client.post(path + "/restore")
        assert restored.status_code == 200, restored.text
        for key in ["transitions", "session_id", "job_id", "evidence", "result", "accepted_at", "accepted_by"]:
            assert restored.json()[key] == before[key]
        if phase == "revoked":
            response = await client.post(path + "/transitions", json={"target": "backlog", "reason": "Withdraw"})
            assert response.status_code == 200, response.text
    finally:
        release.set()
    result = await asyncio.wait_for(running if running is not None else execute(worker), timeout=30)
    saved = (await client.get(path)).json()
    if phase == "revoked":
        assert result["status"] == "failed"
        assert saved["status"] == "backlog" and saved["result"] is None
    else:
        assert result["status"] == "completed"
        assert saved["status"] == "in_review" and saved["result"]["status"] == "COMPLETED"
        assert saved["result"]["run_id"] == run_id
        assert (await client.get("/company/attention")).json()["in_review"] == 1


async def automation(system):
    from agno.company.routines import _CompanyScheduleExecutor, _ensure_automation_schedule

    client, db, worker, os, _ = system
    worker._company_schedule_db = db
    executor = _CompanyScheduleExecutor(
        os, worker.authorization_app, base_url="http://test", internal_service_token="test"
    )
    schedule = await _ensure_automation_schedule(db)
    return executor, schedule


async def tick(executor, db):
    from agno.company.execution import _call

    claimed = await _call(db, "claim_due_schedule", str(uuid4()))
    if claimed is None:
        return None
    return await executor.execute(claimed, db)


@pytest.mark.asyncio
async def test_automation_concurrent_ticks_and_restart(system, monkeypatch):
    from agno.company.execution import _call
    from agno.company.routines import _CompanyScheduleExecutor

    client, db, worker, os, _ = system
    task = await accepted(client)
    executor, schedule = await automation(system)
    results = await asyncio.gather(tick(executor, db), tick(executor, db))
    assert sum(result is not None for result in results) == 1
    result = next(result for result in results if result)
    assert result["status"] == "success", result
    saved = await _call(db, "get_task", task["id"])
    assert saved["job_id"] is not None, result
    run_id = saved["job_id"]
    assert (await worker.store.get_job(run_id))["idempotency_key"] == f"company:{task['id']}:1"
    # A new scheduler after submission sees the same durable Task reservation.
    restarted = _CompanyScheduleExecutor(
        os, worker.authorization_app, base_url="http://test", internal_service_token="test"
    )
    await _call(db, "update_schedule", schedule["id"], next_run_at=0)
    await tick(restarted, db)
    assert (await _call(db, "get_task", task["id"]))["job_id"] == run_id
    assert (await execute(worker))["status"] == "completed"
    assert (await client.get(f"/company/tasks/{task['id']}/runs")).json()["meta"]["total_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("queued", [False, True])
async def test_automation_crash_during_dispatch(system, monkeypatch, queued):
    from agno.company.execution import _call
    from agno.os.routers.company import runs

    client, db, worker, os, _ = system
    task = await accepted(client)
    executor, schedule = await automation(system)
    original = runs._run_route

    async def interrupted(*args, **kwargs):
        if queued:
            await original(*args, **kwargs)
        raise RuntimeError("process stopped before dispatch response")

    monkeypatch.setattr(runs, "_run_route", interrupted)
    first = await tick(executor, db)
    reserved = await _call(db, "get_task", task["id"])
    from agno.db.schemas.tasks import task_run_id

    run_id = task_run_id(task["id"], 1)
    # The existing run route commits the queue ticket before projecting the Task.
    # A pre-submit interruption leaves Ready work; a lost reply retains the attempt.
    assert reserved["status"] == ("in_progress" if queued else "ready"), first
    assert reserved["job_id"] == (run_id if queued else None)
    assert (await worker.store.get_job(run_id) is not None) is queued
    monkeypatch.setattr(runs, "_run_route", original)
    restarted, _ = await automation(system)
    await _call(db, "update_schedule", schedule["id"], next_run_at=0)
    second = await tick(restarted, db)
    assert await worker.store.get_job(run_id) is not None, second
    assert (await _call(db, "get_task", task["id"]))["job_id"] == run_id
    assert (await execute(worker))["status"] == "completed"
    assert (await client.get(f"/company/tasks/{task['id']}/runs")).json()["meta"]["total_count"] == 1


@pytest.mark.asyncio
async def test_automation_backlog_after_queue_never_executes(system):
    client, db, worker, os, _ = system
    task = await accepted(client)
    executor, schedule = await automation(system)
    result = await tick(executor, db)
    path = f"/company/tasks/{task['id']}"
    assert (await client.get(path)).json()["status"] == "in_progress", result
    assert (
        await client.post(path + "/transitions", json={"target": "backlog", "reason": "Withdraw"})
    ).status_code == 200
    assert (await execute(worker))["status"] == "failed"
    assert (await client.get(path)).json()["status"] == "backlog"
    assert "draft" not in json.dumps((await client.get(path)).json().get("result"))


async def intake_proposal(manager, title, evidence, **kwargs):
    from agno.company.routines import _manager_call

    return await _manager_call(
        manager,
        "intake",
        evidence[0]["source_id"],
        "proposal-run",
        dict(
            title=title,
            brief=kwargs.pop("brief", title),
            proposal_key=title,
            evidence_links=[item["link"] for item in evidence],
            evidence_hashes={item["link"]: item["content_hash"] for item in evidence},
        ),
        **kwargs,
    )


async def routine_proposal(system, tmp_path, *, policy=None, executor_id="writer", template="intake"):
    from agno.company.manager import AsyncCompanyManager, CompanyManager
    from agno.company.routines import _manager_call, _RoutineAuthorization
    from agno.run.authorization import authorization_scope

    client, db, worker, os, _ = system
    product = (await client.post("/company/products", json={"name": "Docs"})).json()
    project = (await client.post("/company/projects", json={"product_id": product["id"], "name": "Release"})).json()
    assert (
        await client.post(
            f"/company/projects/{project['id']}/transitions", json={"target": "active", "reason": "Start"}
        )
    ).status_code == 200
    source_path = tmp_path / (product["id"] + ".md")
    source_path.write_text("# Release\nVerified Source material.\n")
    source = (
        await client.post(
            "/company/sources", json={"product_id": product["id"], "type": "markdown", "reference": str(source_path)}
        )
    ).json()
    if policy is None:
        policy = {
            "executor_type": "agent",
            "executor_id": "writer",
            "source_ids": [source["id"]],
            "work_scope": {"product_ids": [product["id"]], "project_ids": [project["id"]]},
            "required_checks": ["project_active", "has_source_evidence", "executor_registered"],
            "limits": {"max_acceptances": 1, "expires_at": int(time.time()) + 3600},
        }
    response = await client.post(
        "/company/routines",
        json={
            "product_id": product["id"],
            "name": template or "custom",
            "template": template,
            **({"instructions": "Inspect work and propose follow-up."} if template is None else {}),
            "executor_type": "agent",
            "executor_id": "writer",
            "cron_expr": "0 0 * * *",
            "auto_accept": policy,
        },
    )
    assert response.status_code == 201, response.text
    routine = response.json()
    manager = AsyncCompanyManager(db, os.registry) if isinstance(db, AsyncBaseDb) else CompanyManager(db, os.registry)
    evidence = await _manager_call(manager, "read_source", source["id"], "source-run")
    evidence = [{key: value for key, value in item.items() if key != "content"} for item in evidence]
    with authorization_scope(lambda: _RoutineAuthorization(None, routine["id"])):
        task = await intake_proposal(
            manager,
            "Draft",
            brief="Write release notes",
            project_id=project["id"],
            executor_type="agent",
            executor_id=executor_id,
            evidence=evidence,
        )
    assert task["origin"] == "routine" and task["routine_id"] == routine["id"]
    return task, routine, manager


@pytest.mark.asyncio
async def test_builtin_checks_on_fresh_deployment_and_policy_limit(system, tmp_path):
    from agno.company.execution import _call
    from agno.company.routines import _RoutineAuthorization
    from agno.run.authorization import authorization_scope

    client, db, worker, os, _ = system
    assert os.company.acceptance_checks == {}
    task, routine, manager = await routine_proposal(system, tmp_path)
    executor, _ = await automation(system)
    with authorization_scope(lambda: _RoutineAuthorization(None, routine["id"])):
        other = await intake_proposal(
            manager,
            "Other",
            project_id=task["project_id"],
            executor_type="agent",
            executor_id="writer",
            evidence=task["evidence"],
        )
    results = await asyncio.gather(executor._accept(task), executor._accept(other), return_exceptions=True)
    assert sum(isinstance(result, dict) for result in results) == 1, results
    assert any("limit" in str(result) for result in results), results
    ready = next(result for result in results if isinstance(result, dict))
    assert ready["status"] == "ready"
    assert await executor._dispatch(ready)
    assert (await execute(worker))["status"] == "completed"
    # Soft deletion and a restart do not replenish the accepted-work budget.
    await _call(db, "transition_task", ready["id"], "cancelled", "Archive reviewed work")
    assert await _call(db, "delete_task", ready["id"])
    loser = other if ready["id"] == task["id"] else task
    with pytest.raises(ValueError, match="limit"):
        await executor._accept(loser)


@pytest.mark.asyncio
async def test_auto_accept_executor_mismatch_revocation_unknown_and_forged_evidence(system, tmp_path):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    task, routine, _ = await routine_proposal(system, tmp_path, executor_id="agent-b")
    executor, _ = await automation(system)
    with pytest.raises(ValueError, match="executor"):
        await executor._accept(task)
    task = await _call(db, "update_task", task["id"], executor_id="writer")
    original = task["evidence"]
    task = await _call(db, "update_task", task["id"], evidence=[{**original[0], "content_hash": "agent-asserted"}])
    with pytest.raises(ValueError, match="has_source_evidence"):
        await executor._accept(task)
    task = await _call(db, "update_task", task["id"], evidence=original)
    # Direct scheduler edits must also fail closed at the acceptance boundary.
    row = await _call(db, "get_schedule", routine["id"])
    payload = row["payload"]
    payload["metadata"]["auto_accept"]["required_checks"] = ["not-installed"]
    await _call(db, "update_schedule", routine["id"], payload=payload)
    with pytest.raises(ValueError, match="Unknown"):
        await executor._accept(task)
    assert (await _call(db, "get_task", task["id"]))["status"] == "backlog"
    result = await tick(executor, db)
    skipped = next(item for item in result["output"]["tasks"] if item["task_id"] == task["id"])
    assert skipped["status"] == "skipped" and "Unknown" in skipped["reason"]
    assert (await client.patch(f"/company/routines/{routine['id']}", json={"auto_accept": False})).status_code == 200
    with pytest.raises(ValueError, match="no human"):
        await executor._accept(task)


@pytest.mark.asyncio
async def test_auto_accept_revocation_after_queue_and_scope_changes_during_check(system, tmp_path):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    task, routine, _ = await routine_proposal(system, tmp_path)
    executor, _ = await automation(system)
    ready = await executor._accept(task)
    await executor._dispatch(ready)
    assert (await client.patch(f"/company/routines/{routine['id']}", json={"auto_accept": False})).status_code == 200
    with pytest.raises(ValueError, match="revoked"):
        await executor._dispatch(ready)
    assert (await execute(worker))["status"] == "failed"
    assert (await _call(db, "get_task", task["id"]))["status"] != "in_review"


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["proposal", "authorization", "expiry", "scope", "sources"])
async def test_auto_accept_rechecks_every_bound_and_check_races(system, tmp_path, change):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path)
    executor, _ = await automation(system)
    schedule = await _call(db, "get_schedule", routine["id"])
    policy = schedule["payload"]["metadata"]["auto_accept"]
    if change in {"proposal", "authorization"}:

        async def check(observed, manager):
            if change == "proposal":
                await _call(db, "update_task", observed["id"], brief="Changed during check")
            else:
                await _call(db, "update_schedule", routine["id"], enabled=False)
            return True

        os.company.acceptance_checks["race"] = check
        policy["required_checks"] = ["race"]
    elif change == "expiry":
        policy["limits"]["expires_at"] = 1
    elif change == "scope":
        policy["work_scope"]["project_ids"] = []
    else:
        policy["source_ids"] = []
    await _call(db, "update_schedule", routine["id"], payload=schedule["payload"])
    with pytest.raises(ValueError):
        await executor._accept(task)
    assert (await _call(db, "get_task", task["id"]))["status"] == "backlog"


@pytest.mark.asyncio
async def test_automation_records_revocation_before_dispatch(system, monkeypatch):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    value = await accepted(client)
    executor, schedule = await automation(system)
    original = executor._dispatch

    async def revoke(task):
        await _call(db, "transition_task", task["id"], "backlog", "Withdraw before dispatch")
        return await original(task)

    monkeypatch.setattr(executor, "_dispatch", revoke)
    result = await tick(executor, db)
    assert result["output"]["tasks"][0]["status"] == "skipped"
    assert "changed" in result["output"]["tasks"][0]["reason"]
    assert (await _call(db, "get_task", value["id"]))["job_id"] is None


@pytest.mark.asyncio
async def test_routine_can_still_propose_projects(system):
    from agno.company.manager import AsyncCompanyManager, CompanyManager
    from agno.company.routines import _manager_call, _RoutineAuthorization
    from agno.run.authorization import authorization_scope

    client, db, worker, os, _ = system
    product = (await client.post("/company/products", json={"name": "Routine projects"})).json()
    manager = AsyncCompanyManager(db, os.registry) if isinstance(db, AsyncBaseDb) else CompanyManager(db, os.registry)
    with authorization_scope(lambda: _RoutineAuthorization(None, "routine")):
        project = await _manager_call(manager, "create_project", product["id"], "Proposed release")
    assert project["status"] == "proposed"
    assert (await _manager_call(manager, "get_project", project["id"]))["product_id"] == product["id"]


@pytest.mark.asyncio
async def test_acceptance_budget_is_per_policy_and_distinct_task(system, tmp_path):
    from agno.company.execution import _call
    from agno.company.routines import _RoutineAuthorization
    from agno.run.authorization import authorization_scope

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path)
    executor, _ = await automation(system)
    first = await executor._accept(task)
    await _call(db, "transition_task", task["id"], "backlog", "Return proposal")
    repeated = await executor._accept(await _call(db, "get_task", task["id"]))
    assert repeated["status"] == "ready"
    assert sum(bool(entry.get("auto_accept")) for entry in repeated["transitions"]) == 2
    with authorization_scope(lambda: _RoutineAuthorization(None, routine["id"])):
        other = await intake_proposal(
            manager,
            "Another task",
            project_id=task["project_id"],
            evidence=task["evidence"],
        )
        third = await intake_proposal(
            manager,
            "Third task",
            project_id=task["project_id"],
            evidence=task["evidence"],
        )
    with pytest.raises(ValueError, match="limit"):
        await executor._accept(other)
    policy = routine["payload"]["metadata"]["auto_accept"]
    policy["limits"]["max_acceptances"] = 2
    response = await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})
    assert response.status_code == 200, response.text
    # The edited policy has a fresh budget of two, not one remaining from its predecessor.
    second = await executor._accept(other)
    last = await executor._accept(third)
    assert second["status"] == last["status"] == "ready"
    assert second["transitions"][-1]["auto_accept"]["policy"] != first["transitions"][-1]["auto_accept"]["policy"]


@pytest.mark.asyncio
async def test_authenticated_intake_without_executor_is_picked_up_once(system, tmp_path):
    from unittest.mock import AsyncMock

    import jwt

    from agno.company.execution import _call
    from agno.os.authz import Authorization
    from agno.registry import Registry
    from agno.scheduler import ScheduleExecutor
    from agno.tools.company import CompanyTools

    _, db, worker, original_os, components = system
    path = tmp_path / "intake.md"
    path.write_text("# API release\nDocument the new API.\n")
    selected = {}
    writes = []

    class IntakeModel(OfflineModel):
        def invoke(self, messages, *args, **kwargs):
            observations = [message for message in messages if message.role == "tool"]
            if not observations:
                name = "read_company_source"
                arguments = {"source_id": selected["source_id"]}
            elif len(observations) == 1:
                index = json.loads(observations[0].content)
                name = "read_company_source"
                arguments = {"source_id": selected["source_id"], "path": index["data"][0]["path"]}
            elif len(observations) == 2:
                evidence = [json.loads(observations[1].content)]
                name = "intake_company_source"
                arguments = {
                    "source_id": selected["source_id"],
                    "title": "Document API",
                    "brief": "Write the release guide",
                    "proposal_key": "api-guide",
                    "evidence_links": [item["link"] for item in evidence],
                    "evidence_hashes": {item["link"]: item["content_hash"] for item in evidence},
                    # Model omission through empty or null arguments remains executor-less.
                    "executor_type": None,
                    "executor_id": "",
                    "project_id": "",
                }
            else:
                return ModelResponse(role="assistant", content="Proposal recorded", response_usage=MessageMetrics())
            return ModelResponse(
                role="assistant",
                tool_calls=[
                    {
                        "id": name,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments)},
                    }
                ],
                response_usage=MessageMetrics(),
            )

    class WriterModel(OfflineModel):
        def invoke(self, *args, **kwargs):
            from agno.run.authorization import current_authorization

            writes.append(current_authorization().context.principal_id)
            return super().invoke(*args, **kwargs)

    writer = components["writer"]
    writer.model = WriterModel()
    reader = Agent(id="reader", model=IntakeModel(), tools=[CompanyTools(db)], db=db, telemetry=False)
    components["reader"] = reader
    secret = "authenticated-intake-secret-at-least-32-bytes"
    scopes = [
        f"{resource}:{action}"
        for resource in ("products", "tasks", "sources", "routines", "schedules", "wiki")
        for action in ("read", "write")
    ] + ["agents:reader:run", "agents:writer:run", "agents:read"]
    token = jwt.encode(
        {"sub": "alice", "aud": "intake-automation", "scopes": scopes, "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )
    os = AgentOS(
        id="intake-automation",
        db=db,
        registry=Registry(agents=[reader, writer]),
        company=CompanyConfig(),
        queue=worker.config,
        telemetry=False,
        user_isolation=True,
        authorization=Authorization(verification_keys=[secret], algorithm="HS256"),
    )
    app = os.get_app()
    app.state.queue_worker = worker
    app.state.internal_service_token = "test"
    worker.authorization_app = app
    worker._company_schedule_db = db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"Authorization": "Bearer " + token}
    ) as client:
        product = (await client.post("/company/products", json={"name": "API"})).json()
        selected["source_id"] = (
            await client.post(
                "/company/sources", json={"product_id": product["id"], "type": "markdown", "reference": str(path)}
            )
        ).json()["id"]
        response = await client.post(
            "/company/routines",
            json={
                "product_id": product["id"],
                "name": "intake",
                "template": "intake",
                "executor_type": "agent",
                "executor_id": "reader",
                "cron_expr": "0 0 1 1 *",
                "auto_accept": {
                    "executor_type": "agent",
                    "executor_id": "writer",
                    "source_ids": [selected["source_id"]],
                    "limits": {"expires_at": int(time.time()) + 3600},
                },
            },
        )
        assert response.status_code == 201, response.text
        routine = response.json()
        original_request = client.request

        async def request_and_work(method, url, **kwargs):
            result = await original_request(method, url, **kwargs)
            if method == "POST" and result.status_code == 202:
                assert (await execute(worker))["status"] == "completed"
            return result

        intake = ScheduleExecutor(base_url="http://test", internal_service_token="test", poll_interval=0)
        intake._get_client = AsyncMock(return_value=SimpleClient(request_and_work))
        result = await intake.execute(await _call(db, "get_schedule", routine["id"]), db, release_schedule=False)
        assert result["status"] == "success", result
        rows, count = await _call(db, "get_tasks", product_id=product["id"])
        assert count == 1, result
        proposal = rows[0]
        assert proposal["status"] == "backlog" and proposal["executor_id"] is None
        assert proposal["executor_type"] is None and proposal["routine_id"] == routine["id"]
        executor, schedule = await automation((client, db, worker, os, components))
        ticks = await asyncio.gather(tick(executor, db), tick(executor, db))
        assert sum(value is not None for value in ticks) == 1
        task = await _call(db, "get_task", proposal["id"])
        assert task["status"] == "in_progress", ticks
        assert task["executor_id"] == "writer" and task["accepted_by"] == "alice"
        job = await worker.store.get_job(task["job_id"])
        assert job["user_id"] == "alice"
        assert job["idempotency_key"] == "company:" + task["id"] + ":1"
        assert (await execute(worker))["status"] == "completed"
        await _call(db, "update_schedule", schedule["id"], next_run_at=0)
        await asyncio.gather(tick(executor, db), tick(executor, db))
        assert await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds) is None
        assert writes == ["alice"]
        assert (await _call(db, "get_task", task["id"]))["status"] == "in_review"
        history = (await client.get("/company/tasks/" + task["id"] + "/runs")).json()
        assert history["meta"]["total_count"] == 1


@pytest.mark.asyncio
async def test_exhausted_policy_skips_source_reads_on_every_tick(system, tmp_path, monkeypatch):
    import agno.company.sources as sources
    from agno.company.execution import _call
    from agno.company.routines import _RoutineAuthorization
    from agno.run.authorization import authorization_scope

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path)
    executor, schedule = await automation(system)
    reads = []
    original = sources.read_source

    def counted(source, run_id, *args, **kwargs):
        reads.append(run_id)
        return original(source, run_id, *args, **kwargs)

    monkeypatch.setattr(sources, "read_source", counted)
    await executor._accept(task)
    # Source bounds and the named evidence check share one fresh read.
    assert len(reads) == 1
    with authorization_scope(lambda: _RoutineAuthorization(None, routine["id"])):
        other = await intake_proposal(
            manager,
            "Another proposal",
            project_id=task["project_id"],
            evidence=task["evidence"],
        )
    # Deleted accepted Tasks still spend the budget, including after a restart.
    await _call(db, "transition_task", task["id"], "cancelled", "Archive accepted work")
    await _call(db, "delete_task", task["id"])
    executor, schedule = await automation(system)
    for _ in range(3):
        reads.clear()
        await _call(db, "update_schedule", schedule["id"], next_run_at=0)
        result = await tick(executor, db)
        assert reads == []
        assert result["output"]["tasks"] == [
            {"task_id": other["id"], "status": "skipped", "reason": "Routine acceptance limit reached"}
        ]
        assert (await _call(db, "get_task", other["id"]))["status"] == "backlog"
    # Editing the policy immediately opens its own budget; a skip is not cached forever.
    policy = routine["payload"]["metadata"]["auto_accept"]
    policy["limits"]["max_acceptances"] = 2
    assert (await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})).status_code == 200
    await _call(db, "update_schedule", schedule["id"], next_run_at=0)
    await tick(executor, db)
    assert len(reads) == 1
    assert (await execute(worker))["status"] == "completed"


@pytest.mark.asyncio
async def test_automatic_checks_retry_when_server_fact_changes(system, tmp_path, monkeypatch):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path)
    executor, _ = await automation(system)
    await _call(db, "delete_project", task["project_id"])
    with pytest.raises(ValueError, match="project_active"):
        await executor._accept(task)
    with monkeypatch.context() as clock:
        clock.setattr(time, "time", lambda: (task["updated_at"] or task["created_at"]) + 1)
        await _call(db, "restore_project", task["project_id"])
    # A later restoration timestamp must refuse the stale proposal.
    with pytest.raises(ValueError, match="Proposal changed"):
        await executor._accept(task)
    task = await _call(db, "get_task", task["id"])
    assert (await executor._accept(task))["status"] == "ready"


@pytest.mark.asyncio
async def test_runtime_automation_schedule_rejects_public_mutation(system, tmp_path):
    from agno.company.execution import _call
    from agno.scheduler import ScheduleManager
    from agno.tools.scheduler import SchedulerTools

    client, db, worker, os, _ = system
    task, routine, _ = await routine_proposal(system, tmp_path)
    executor, schedule = await automation(system)
    path = "/schedules/" + schedule["id"]
    for response in [
        await client.patch(path, json={"enabled": False}),
        await client.patch(path, json={"cron_expr": "0 0 * * *"}),
        await client.delete(path),
        await client.post(path + "/enable"),
        await client.post(path + "/disable"),
        await client.post(path + "/trigger"),
    ]:
        assert response.status_code == 409, response.text
        assert "runtime-managed" in response.json()["detail"]
    manager = ScheduleManager(db)
    for method in ("update", "delete", "enable", "disable", "aupdate", "adelete", "aenable", "adisable"):
        with pytest.raises(ValueError, match="runtime-managed"):
            if method.startswith("a"):
                await getattr(manager, method)(schedule["id"])
            else:
                getattr(manager, method)(schedule["id"])
    tools = SchedulerTools(db=db)
    assert "runtime-managed" in json.loads(tools.disable_schedule(schedule["id"]))["error"]
    assert "runtime-managed" in json.loads(await tools.adisable_schedule(schedule["id"]))["error"]
    # User Routines still support the existing pause/resume domain.
    assert (await client.post("/schedules/" + routine["id"] + "/disable")).status_code == 200
    assert (await client.post("/schedules/" + routine["id"] + "/enable")).status_code == 200
    restarted, saved = await automation(system)
    assert saved["enabled"] is True
    await _call(db, "update_schedule", schedule["id"], next_run_at=0)
    assert (await tick(restarted, db))["status"] == "success"
    assert (await execute(worker))["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["check", "executor"])
async def test_generic_schedule_patch_validates_automatic_policy(system, tmp_path, invalid):
    import copy

    from agno.company.execution import _call

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path)
    before = await _call(db, "get_schedule", routine["id"])
    payload = copy.deepcopy(before["payload"])
    policy = payload["metadata"]["auto_accept"]
    if invalid == "check":
        policy["required_checks"] = ["unknown_check"]
    else:
        policy["executor_id"] = "missing-executor"
    response = await client.patch("/schedules/" + routine["id"], json={"payload": payload})
    assert response.status_code == 422, response.text
    assert (await _call(db, "get_schedule", routine["id"])) == before
    # Application checks use the same validation path as built-ins.
    os.company.acceptance_checks["application_check"] = lambda task, manager: True
    payload = copy.deepcopy(before["payload"])
    payload["metadata"]["auto_accept"]["required_checks"] = ["application_check"]
    response = await client.patch("/schedules/" + routine["id"], json={"payload": payload})
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_automation_filters_candidates_before_paging(system, monkeypatch):
    import inspect

    from agno.company.execution import _call

    client, db, worker, os, _ = system
    ready = await accepted(client)
    backlog = await accepted(client)
    await _call(db, "transition_task", backlog["id"], "backlog", "Revise")
    running = await accepted(client)
    executor, _ = await automation(system)
    await executor._dispatch(await _call(db, "get_task", running["id"]))
    # Enough terminal history to dominate an unfiltered page.
    for index in range(101):
        row = {**ready, "id": "completed-" + str(index), "status": "done"}
        await _call(db, "create_task", row)
    queries = []
    returned = []
    original = db.get_tasks

    def record(kwargs, result):
        queries.append(kwargs)
        returned.extend(row["id"] for row in result[0])
        return result

    def observed(**kwargs):
        return record(kwargs, original(**kwargs))

    async def aobserved(**kwargs):
        return record(kwargs, await original(**kwargs))

    monkeypatch.setattr(db, "get_tasks", aobserved if inspect.iscoroutinefunction(original) else observed)
    outcomes = await executor._tick()
    assert {query["status"] for query in queries} == {"backlog", "ready", "in_progress"}
    assert set(returned) == {ready["id"], backlog["id"], running["id"]}
    assert {outcome["task_id"] for outcome in outcomes} == {ready["id"], running["id"]}
    assert any(outcome["status"] == "already_submitted" for outcome in outcomes)


@pytest.mark.asyncio
async def test_refresh_completion_requires_permission_and_never_completes_on_archive(system, tmp_path):
    from agno.company.execution import _call
    from agno.company.routines import _manager_call

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path, template="refresh")
    await _manager_call(manager, "transition_task", task["id"], "cancelled", "No longer needed")
    executor, schedule = await automation(system)
    # Terminal work alone is not a completion proposal.
    assert await executor._tick() == []
    refreshed = await _manager_call(manager, "refresh", task["product_id"])
    assert refreshed["completion_proposals"][0]["project_id"] == task["project_id"]
    outcomes = await executor._tick()
    assert outcomes == [
        {
            "project_id": task["project_id"],
            "status": "skipped",
            "reason": "Routine is not authorized to complete Projects",
        }
    ]
    assert (await _manager_call(manager, "get_project", task["project_id"]))["status"] == "active"
    policy = routine["payload"]["metadata"]["auto_accept"]
    policy["complete_projects"] = True
    assert (await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})).status_code == 200
    # Refresh may archive terminal records, but even an authorized Routine cannot
    # accept a Backlog Task or close an active Project itself.
    old = int(time.time()) - 30 * 86400
    await _call(
        db,
        "create_task",
        dict(
            id="old-terminal",
            product_id=task["product_id"],
            title="Old",
            status="done",
            created_at=old,
            updated_at=old,
            transitions=[],
        ),
    )
    backlog = await _manager_call(manager, "create_task", task["product_id"], "Needs human review")
    refreshed = await _manager_call(manager, "refresh", task["product_id"])
    assert "old-terminal" in refreshed["archived_tasks"]
    assert (await _manager_call(manager, "get_task", backlog["id"]))["status"] == "backlog"
    assert (await _manager_call(manager, "get_project", task["project_id"]))["status"] == "active"
    assert (await _manager_call(manager, "get_task", task["id"]))["status"] == "cancelled"
    results = await asyncio.gather(tick(executor, db), tick(executor, db))
    assert sum(result is not None for result in results) == 1
    project = await _manager_call(manager, "get_project", task["project_id"])
    assert project["status"] == "done"
    assert len([entry for entry in project["transitions"] if entry["target"] == "done"]) == 1
    receipt = project["transitions"][-1]["auto_accept"]
    assert receipt["routine_id"] == routine["id"]
    assert await _call(db, "count_company_acceptances", routine["id"], receipt["policy"], "") == 1
    assert await worker.store.claim_job(worker.worker_id, worker.config.lock_grace_seconds) is None
    assert await executor._tick() == []


@pytest.mark.asyncio
async def test_project_completion_and_task_acceptance_share_atomic_budget(system, tmp_path):
    from agno.company.execution import _call
    from agno.company.routines import _manager_call, _policy_fingerprint

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path, template="refresh")
    await _manager_call(manager, "transition_task", task["id"], "cancelled", "Finished")
    policy = routine["payload"]["metadata"]["auto_accept"]
    policy.update(complete_projects=True, required_checks=["has_source_evidence", "executor_registered"])
    policy["work_scope"]["project_ids"].append(None)
    assert (await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})).status_code == 200
    other = await intake_proposal(manager, "Independent task", task["evidence"], routine_id=routine["id"])
    await _manager_call(manager, "refresh", task["product_id"])
    executor, _ = await automation(system)
    project = await _manager_call(manager, "get_project", task["project_id"])
    proposal = await executor._completion_candidate(manager, project, routine["id"])
    results = await asyncio.gather(
        executor._accept(other), executor._accept(proposal, completing=True), return_exceptions=True
    )
    assert sum(isinstance(result, dict) for result in results) == 1, results
    assert any("limit" in str(result) for result in results), results
    current = await _call(db, "get_schedule", routine["id"])
    assert await _call(db, "count_company_acceptances", routine["id"], _policy_fingerprint(current), "") == 1
    winner = next(result for result in results if isinstance(result, dict))
    if winner["status"] == "ready":
        await _call(db, "transition_task", winner["id"], "cancelled", "Archive accepted work")
    await _call(db, "delete_project" if winner["status"] == "done" else "delete_task", winner["id"])
    assert await _call(db, "count_company_acceptances", routine["id"], _policy_fingerprint(current), "") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "restriction", ["scope", "expiry", "revoked", "check", "source", "changed_task", "changed_project"]
)
async def test_project_completion_enforces_live_policy_and_terminal_tasks(system, tmp_path, monkeypatch, restriction):
    from agno.company.execution import _call
    from agno.company.routines import _manager_call

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path, template="refresh")
    await _manager_call(manager, "transition_task", task["id"], "cancelled", "Finished")
    policy = routine["payload"]["metadata"]["auto_accept"]
    policy["complete_projects"] = True
    if restriction == "scope":
        policy["work_scope"]["project_ids"] = []
    elif restriction == "expiry":
        policy["limits"]["expires_at"] = 1
    elif restriction == "source":
        policy["source_ids"] = []
    elif restriction in {"check", "changed_task", "changed_project"}:

        async def check(proposal, check_manager):
            if restriction == "changed_project":
                with monkeypatch.context() as clock:
                    clock.setattr(time, "time", lambda: proposal["updated_at"] + 1)
                    await _call(db, "update_project", proposal["id"], name="Changed during checks")
                return True
            if restriction == "changed_task":
                await _call(
                    db,
                    "create_task",
                    dict(
                        id="new-open",
                        product_id=task["product_id"],
                        project_id=task["project_id"],
                        title="New work",
                        status="backlog",
                        created_at=int(time.time()),
                        transitions=[],
                    ),
                )
                return True
            return False

        os.company.acceptance_checks["completion_check"] = check
        policy["required_checks"].append("completion_check")
    assert (await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})).status_code == 200
    await _manager_call(manager, "refresh", task["product_id"])
    executor, _ = await automation(system)
    project = await _manager_call(manager, "get_project", task["project_id"])
    proposal = await executor._completion_candidate(manager, project, routine["id"])
    if restriction == "revoked":
        assert (
            await client.patch("/company/routines/" + routine["id"], json={"auto_accept": False})
        ).status_code == 200
    with pytest.raises(ValueError):
        await executor._accept(proposal, completing=True)
    assert (await _manager_call(manager, "get_project", task["project_id"]))["status"] == "active"


@pytest.mark.asyncio
@pytest.mark.parametrize("binding", ["product_id", "template"])
async def test_completion_rechecks_routine_binding(system, tmp_path, binding):
    from agno.company.execution import _call
    from agno.company.routines import _manager_call, _policy_fingerprint

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path, template="refresh")
    await _manager_call(manager, "transition_task", task["id"], "cancelled", "Finished")
    other = (await client.post("/company/products", json={"name": "Other"})).json()

    async def change_binding():
        current = await _call(db, "get_schedule", routine["id"])
        before = _policy_fingerprint(current)
        payload = current["payload"]
        payload["metadata"][binding] = other["id"] if binding == "product_id" else "intake"
        response = await client.patch("/schedules/" + routine["id"], json={"payload": payload})
        assert response.status_code == 200, response.text
        assert _policy_fingerprint(await _call(db, "get_schedule", routine["id"])) == before

    async def check(proposal, check_manager):
        await change_binding()
        return True

    os.company.acceptance_checks["binding_check"] = check
    policy = routine["payload"]["metadata"]["auto_accept"]
    policy.update(complete_projects=True, required_checks=["executor_registered", "binding_check"])
    assert (await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})).status_code == 200
    await _manager_call(manager, "refresh", task["product_id"])
    executor, _ = await automation(system)
    project = await _manager_call(manager, "get_project", task["project_id"])
    proposal = await executor._completion_candidate(manager, project, routine["id"])
    assert proposal is not None
    with pytest.raises(ValueError, match="Routine automatic acceptance changed"):
        await executor._accept(proposal, completing=True)
    assert (await _manager_call(manager, "get_project", task["project_id"]))["status"] == "active"
    current = await _call(db, "get_schedule", routine["id"])
    assert await _call(db, "count_company_acceptances", routine["id"], _policy_fingerprint(current), "") == 0


@pytest.mark.asyncio
async def test_automation_schedule_follows_company_lifespan(system, monkeypatch):
    from agno.company.execution import _call
    from agno.company.routines import _AUTOMATION_SCHEDULE_ID, _CompanyScheduleExecutor
    from agno.db.schemas.scheduler import Schedule
    from agno.os.app import scheduler_lifespan
    from agno.scheduler import SchedulePoller

    client, db, worker, os, _ = system
    app = worker.authorization_app
    company = os.company
    os._internal_service_token = "test"

    # Drive real claims deterministically, after the actual lifespan setup.
    async def start(poller):
        pass

    monkeypatch.setattr(SchedulePoller, "start", start)
    os.company = None
    async with scheduler_lifespan(app, os):
        assert await _call(db, "get_schedule", _AUTOMATION_SCHEDULE_ID) is None
    os.company = company
    async with scheduler_lifespan(app, os):
        assert (await _call(db, "get_schedule", _AUTOMATION_SCHEDULE_ID))["enabled"] is True
    await _call(db, "update_schedule", _AUTOMATION_SCHEDULE_ID, next_run_at=0)
    unrelated = Schedule(id="unrelated", name="Unrelated", cron_expr="* * * * *", endpoint="/health", next_run_at=0)
    await _call(db, "create_schedule", unrelated.to_dict())
    os.company = None
    for restart in range(2):
        async with scheduler_lifespan(app, os):
            assert (await _call(db, "get_schedule", _AUTOMATION_SCHEDULE_ID))["enabled"] is False
            claimed = await _call(db, "claim_due_schedule", "off-worker")
            if restart == 0:
                assert claimed is not None and claimed["id"] == unrelated.id
                await _call(db, "delete_schedule", unrelated.id)
            else:
                assert claimed is None
            assert await _call(db, "claim_due_schedule", "off-worker") is None
    os.company = company
    async with scheduler_lifespan(app, os):
        assert isinstance(app.state.scheduler_executor, _CompanyScheduleExecutor)
        assert (await _call(db, "get_schedule", _AUTOMATION_SCHEDULE_ID))["enabled"] is True
        result = await tick(app.state.scheduler_executor, db)
        assert result["status"] == "success", result


@pytest.mark.asyncio
async def test_all_task_and_project_writes_stamp_updated_at(system, monkeypatch):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    product = (await client.post("/company/products", json={"name": "Timestamps"})).json()
    project = (await client.post("/company/projects", json={"product_id": product["id"], "name": "Project"})).json()
    task = (
        await client.post(
            "/company/tasks", json={"product_id": product["id"], "project_id": project["id"], "title": "Task"}
        )
    ).json()
    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now)

    async def write(method, *args, **kwargs):
        nonlocal now
        now += 1
        result = await _call(db, method, *args, **kwargs)
        assert result is not None
        assert result["updated_at"] == now, method
        return result

    await write("update_project", project["id"], name="Edited")
    await write("transition_project", project["id"], "active", "Start")
    await write("update_task", task["id"], brief="Edited")
    ready = await write("transition_task", task["id"], "ready", "Accept", executor_type="agent", executor_id="writer")
    running = await write("start_task_run", task["id"], 1, ready["transitions"])
    failed = await write("complete_task_run", task["id"], running["job_id"], {"status": "ERROR"})
    assert failed["status"] == "in_progress"
    completed = await write("complete_task_run", task["id"], running["job_id"], {"status": "COMPLETED"})
    assert completed["status"] == "in_review"
    await write("transition_task", task["id"], "done", "Review accepted")
    await write("transition_project", project["id"], "done", "All work finished")
    # Direct and cascading archives/restores must stamp every affected child.
    for kind, record in (("task", task), ("project", project), ("product", product)):
        children = [("task", task)] if kind == "task" else [("task", task), ("project", project)]
        for method, archived in (("delete_", True), ("restore_", False)):
            now += 1
            assert await _call(db, method + kind, record["id"])
            for child_kind, child in children:
                saved = await _call(db, "get_" + child_kind, child["id"], include_deleted=True)
                assert saved["updated_at"] == now, (method, kind, child_kind)
                assert (saved["deleted_at"] is not None) is archived


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["task", "project"])
@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("timestamp", [None, 100])
async def test_transition_updated_at_compare_and_set(system, monkeypatch, kind, automatic, timestamp):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    product = (await client.post("/company/products", json={"name": "CAS"})).json()
    record = await _call(
        db,
        "create_" + kind,
        dict(
            id=str(uuid4()),
            product_id=product["id"],
            **(
                {"title": "Task", "status": "backlog", "routine_id": "routine"}
                if kind == "task"
                else {"name": "Project", "status": "active"}
            ),
            created_at=1,
            updated_at=timestamp,
            transitions=[],
        ),
    )
    if kind == "project":
        await _call(
            db,
            "create_task",
            dict(
                id=str(uuid4()),
                product_id=product["id"],
                project_id=record["id"],
                title="Finished",
                status="done",
                created_at=1,
                transitions=[],
            ),
        )
    options = {"executor_type": "agent", "executor_id": "writer"} if kind == "task" else {}
    target = "ready" if kind == "task" else "done"
    if automatic:
        options["auto_accept"] = {"routine_id": "routine", "policy": "version", "max_acceptances": 1}
        with pytest.raises(ValueError, match="requires expected_updated_at"):
            await _call(db, "transition_" + kind, record["id"], target, "Accept", **options)
    # Wrong timestamps (including NULL versus an integer) never transition.
    if timestamp is not None:
        assert (
            await _call(
                db, "transition_" + kind, record["id"], target, "Stale NULL", expected_updated_at=None, **options
            )
            is None
        )
    assert (
        await _call(db, "transition_" + kind, record["id"], target, "Stale", expected_updated_at=101, **options) is None
    )
    assert (await _call(db, "get_" + kind, record["id"]))["status"] == record["status"]
    monkeypatch.setattr(time, "time", lambda: 102)
    accepted = await _call(
        db, "transition_" + kind, record["id"], target, "Accept", expected_updated_at=timestamp, **options
    )
    assert accepted["status"] == target
    assert accepted["updated_at"] == 102
    if automatic:
        assert await _call(db, "count_company_acceptances", "routine", "version", "") == 1


@pytest.mark.asyncio
async def test_same_second_timestamp_keeps_status_guard(system, monkeypatch):
    from agno.company.execution import _call

    client, db, worker, os, _ = system
    product = (await client.post("/company/products", json={"name": "Epoch seconds"})).json()
    task = (await client.post("/company/tasks", json={"product_id": product["id"], "title": "First"})).json()
    monkeypatch.setattr(time, "time", lambda: 100)
    observed = await _call(db, "update_task", task["id"], title="Observed")
    await _call(db, "update_task", task["id"], title="Edited in the same second")
    options = dict(expected_updated_at=observed["updated_at"], executor_type="agent", executor_id="writer")
    accepted = await _call(db, "transition_task", task["id"], "ready", "Accept", **options)
    assert accepted["title"] == "Edited in the same second"
    assert accepted["updated_at"] == observed["updated_at"]
    with pytest.raises(ValueError, match="Invalid task transition"):
        await _call(db, "transition_task", task["id"], "ready", "Duplicate", **options)
    assert (
        len([entry for entry in (await _call(db, "get_task", task["id"]))["transitions"] if entry["target"] == "ready"])
        == 1
    )


async def routine_executor(system):
    from unittest.mock import AsyncMock

    from agno.scheduler.executor import ScheduleExecutor

    client, _, worker, _, _ = system
    worker.authorization_app.state.internal_service_token = "contract-internal"

    async def request_and_work(method, url, **kwargs):
        response = await client.request(method, url, **kwargs)
        if method == "POST" and response.status_code == 202:
            job = await execute(worker)
            assert job["status"] == "completed", job
        return response

    executor = ScheduleExecutor(base_url="http://test", internal_service_token="contract-internal", poll_interval=0)
    executor._get_client = AsyncMock(return_value=SimpleClient(request_and_work))
    return executor


@pytest.mark.asyncio
async def test_template_free_routine_quiet_run_and_edited_executor(system):
    from agno.company.execution import _call

    client, db, _, _, components = system
    observed = []

    class CapturingModel(OfflineModel):
        def invoke(self, messages, *args, **kwargs):
            observed.append([message.content for message in messages if message.role == "user"])
            return super().invoke(messages, *args, **kwargs)

    components["writer"].model = CapturingModel()
    components["editors"].model = CapturingModel()
    product = (await client.post("/company/products", json={"name": "Quiet discovery"})).json()
    created = await client.post(
        "/company/routines",
        json=dict(
            product_id=product["id"],
            name="quiet",
            instructions="First custom instructions",
            executor_type="agent",
            executor_id="writer",
            cron_expr="0 * * * *",
        ),
    )
    assert created.status_code == 201, created.text
    routine = created.json()
    executor = await routine_executor(system)
    first = await executor.execute(await _call(db, "get_schedule", routine["id"]), db, release_schedule=False)
    assert first["status"] == "success", first
    assert any("First custom instructions" in str(value) for value in observed)
    edited = await client.patch(
        "/company/routines/" + routine["id"],
        json=dict(
            name="edited",
            instructions="Second custom instructions",
            executor_type="team",
            executor_id="editors",
            cron_expr="0 9 * * *",
        ),
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["target_id"] == "editors" and edited.json()["target_type"] == "team"
    observed.clear()
    second = await executor.execute(await _call(db, "get_schedule", routine["id"]), db, release_schedule=False)
    assert second["status"] == "success", second
    assert any("Second custom instructions" in str(value) for value in observed)
    assert (await _call(db, "get_tasks", product_id=product["id"]))[1] == 0
    assert (await _call(db, "get_sources", product_id=product["id"]))[1] == 0
    history = (await client.get("/company/routines/" + routine["id"] + "/runs")).json()
    assert len(history["data"]) == 2 and all(row["status"] == "success" for row in history["data"])


@pytest.mark.asyncio
async def test_search_routine_adds_website_and_deduplicates_three_runs(system, monkeypatch):
    from agno.company.execution import _call
    from agno.knowledge.document import Document
    from agno.tools.company import CompanyTools

    client, db, worker, os, components = system
    url = "https://example.test/discovered-release"
    monkeypatch.setattr(
        "agno.knowledge.reader.website_reader.WebsiteReader.read",
        lambda *args, **kwargs: [Document(content="The released API needs a migration guide.")],
    )
    product = (await client.post("/company/products", json={"name": "Search discovery"})).json()

    class SearchModel(OfflineModel):
        def invoke(self, messages, *args, **kwargs):
            results = [json.loads(message.content) for message in messages if message.role == "tool"]
            if not results:
                name, arguments = "add_company_source", dict(product_id=product["id"], type="website", reference=url)
            elif len(results) == 1:
                name, arguments = "read_company_source", dict(source_id=results[0]["id"], path=url)
            elif len(results) == 2:
                observed = results[1]
                assert "migration guide" in observed["content"]
                name, arguments = (
                    "intake_company_source",
                    dict(
                        source_id=results[0]["id"],
                        title="Write migration guide",
                        brief="Explain the released API migration",
                        proposal_key=observed["content_hash"],
                        evidence_links=[observed["link"]],
                        evidence_hashes={observed["link"]: observed["content_hash"]},
                    ),
                )
            else:
                return super().invoke(messages, *args, **kwargs)
            return ModelResponse(
                role="assistant",
                tool_calls=[
                    {"id": name, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}
                ],
                response_usage=MessageMetrics(),
            )

    components["writer"].model = SearchModel()
    components["writer"].tools = [CompanyTools(db)]
    os.resync(worker.authorization_app)
    created = await client.post(
        "/company/routines",
        json=dict(
            product_id=product["id"],
            name="search",
            instructions="Discover useful pages, save website Sources, and propose evidence-backed work.",
            executor_type="agent",
            executor_id="writer",
            cron_expr="0 * * * *",
        ),
    )
    assert created.status_code == 201, created.text
    routine = created.json()
    executor = await routine_executor(system)
    runs = []
    for _ in range(3):
        result = await executor.execute(await _call(db, "get_schedule", routine["id"]), db, release_schedule=False)
        assert result["status"] == "success", result
        runs.append(result["run_id"])
    sources, count = await _call(db, "get_sources", product_id=product["id"])
    assert count == 1
    assert sources[0]["config"]["metadata"] == {"agent_id": "writer", "run_id": runs[0]}
    tasks, count = await _call(db, "get_tasks", product_id=product["id"])
    assert count == 1 and tasks[0]["status"] == "backlog"
    assert tasks[0]["evidence"][0]["run_id"] == runs[0]
    assert tasks[0]["evidence"][0]["link"] == url and tasks[0]["evidence"][0]["content_hash"]
    assert tasks[0]["routine_id"] == routine["id"]
    listed = (await client.get("/company/sources", params={"product_id": product["id"]})).json()["data"]
    assert listed[0]["config"]["metadata"]["agent_id"] == "writer"
    # Discovered websites use the same bounded acceptance checks as human-added Sources.
    policy = dict(
        executor_type="agent",
        executor_id="writer",
        source_ids=[sources[0]["id"]],
        required_checks=["has_source_evidence", "executor_registered"],
        limits={"expires_at": int(time.time()) + 3600},
    )
    authorized = await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})
    assert authorized.status_code == 200, authorized.text
    automatic, _ = await automation(system)
    assert (await automatic._accept(tasks[0]))["status"] == "ready"
    assert (await client.delete("/company/sources/" + sources[0]["id"])).status_code == 204
    assert (await client.get("/company/sources", params={"product_id": product["id"]})).json()["data"] == []


@pytest.mark.asyncio
async def test_template_free_policy_never_completes_projects(system, tmp_path):
    from agno.company.execution import _call
    from agno.company.routines import _manager_call, _policy_fingerprint

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path, template=None)
    assert routine["payload"]["metadata"]["template"] is None
    await _manager_call(manager, "transition_task", task["id"], "cancelled", "Finished")
    policy = routine["payload"]["metadata"]["auto_accept"]
    policy["complete_projects"] = True
    assert (await client.patch("/company/routines/" + routine["id"], json={"auto_accept": policy})).status_code == 200
    await _manager_call(manager, "refresh", task["product_id"])
    executor, _ = await automation(system)
    project = await _manager_call(manager, "get_project", task["project_id"])
    proposal = await executor._completion_candidate(manager, project, routine["id"])
    assert proposal is not None
    with pytest.raises(ValueError, match="not authorized to complete Projects"):
        await executor._accept(proposal, completing=True)
    assert await executor._tick() == []
    assert (await _manager_call(manager, "get_project", project["id"]))["status"] == "active"
    current = await _call(db, "get_schedule", routine["id"])
    assert await _call(db, "count_company_acceptances", routine["id"], _policy_fingerprint(current), "") == 0


@pytest.mark.asyncio
async def test_routine_instruction_edit_preserves_fingerprint_and_spent_budget(system, tmp_path):
    from agno.company.execution import _call
    from agno.company.routines import _policy_fingerprint

    client, db, worker, os, _ = system
    task, routine, manager = await routine_proposal(system, tmp_path)
    executor, _ = await automation(system)
    assert (await executor._accept(task))["status"] == "ready"
    before = await _call(db, "get_schedule", routine["id"])
    fingerprint = _policy_fingerprint(before)
    count = await _call(db, "count_company_acceptances", routine["id"], fingerprint, "")
    assert count == 1
    edited = await client.patch(
        "/company/routines/" + routine["id"], json={"instructions": "Use the revised review instructions."}
    )
    assert edited.status_code == 200, edited.text
    after = await _call(db, "get_schedule", routine["id"])
    assert after["payload"]["message"].endswith("Use the revised review instructions.")
    assert _policy_fingerprint(after) == fingerprint
    assert await _call(db, "count_company_acceptances", routine["id"], fingerprint, "") == count
    other = await intake_proposal(
        manager, "Another proposal", task["evidence"], project_id=task["project_id"], routine_id=routine["id"]
    )
    with pytest.raises(ValueError, match="acceptance limit reached"):
        await executor._accept(other)
    assert (await _call(db, "get_task", other["id"]))["status"] == "backlog"
