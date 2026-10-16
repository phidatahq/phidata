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
from agno.run.base import RunStatus
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
        assert run.status == RunStatus.error
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
@pytest.mark.parametrize("executor_type,executor_id", [("agent", "writer"), ("team", "editors")])
async def test_search_routine_adds_website_and_deduplicates_three_runs(system, monkeypatch, executor_type, executor_id):
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

    components[executor_id].model = SearchModel()
    components[executor_id].tools = [CompanyTools(db)]
    os.resync(worker.authorization_app)
    created = await client.post(
        "/company/routines",
        json=dict(
            product_id=product["id"],
            name="search",
            instructions="Discover useful pages, save website Sources, and propose evidence-backed work.",
            executor_type=executor_type,
            executor_id=executor_id,
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
    assert sources[0]["config"]["metadata"] == {"agent_id": executor_id, "run_id": runs[0]}
    tasks, count = await _call(db, "get_tasks", product_id=product["id"])
    assert count == 1 and tasks[0]["status"] == "backlog"
    assert tasks[0]["evidence"][0]["run_id"] == runs[0]
    assert tasks[0]["evidence"][0]["link"] == url and tasks[0]["evidence"][0]["content_hash"]
    assert tasks[0]["routine_id"] == routine["id"]
    listed = (await client.get("/company/sources", params={"product_id": product["id"]})).json()["data"]
    assert listed[0]["config"]["metadata"]["agent_id"] == executor_id
    assert (await client.delete("/company/sources/" + sources[0]["id"])).status_code == 204
    assert (await client.get("/company/sources", params={"product_id": product["id"]})).json()["data"] == []
