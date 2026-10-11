"""Queue polls distinguish an attempt error from a settled durable job."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent
from agno.db.in_memory import InMemoryDb
from agno.db.schemas.jobs import QueuedJob
from agno.job_queue.config import QueueConfig
from agno.job_queue.store import InMemoryQueueStore
from agno.os import AgentOS
from agno.os.job_queue import QueueWorker
from agno.run.agent import RunErrorEvent, RunOutput
from agno.run.base import RunStatus
from agno.session import AgentSession


@pytest.fixture(params=[ClaudeAgent, CodexAgent])
def harness(request):
    db = InMemoryDb()
    agent = request.param(id="test", db=db)
    run = RunOutput(
        run_id="r",
        agent_id="test",
        session_id="s",
        status=RunStatus.error,
        content="attempt failed",
        metadata={"retryable": True},
        queue_attempt=1,
    )
    db.upsert_session(AgentSession(session_id="s", agent_id="test", user_id="owner", runs=[run]))
    store = InMemoryQueueStore()
    store._jobs["r"] = QueuedJob(
        id="r",
        component_type="agent",
        component_id="test",
        session_id="s",
        user_id="owner",
        payload={},
        max_attempts=3,
    ).to_dict()
    store._jobs["r"]["attempt"] = 1
    app = AgentOS(agents=[agent], telemetry=False).get_app()
    app.state.queue_worker = SimpleNamespace(store=store)

    @app.middleware("http")
    async def scope(request, call_next):
        request.state.user_id = request.headers.get("x-test-user", "owner")
        request.state.user_isolation_enabled = True
        return await call_next(request)

    return SimpleNamespace(app=app, client=TestClient(app), db=db, store=store, run=run)


@pytest.mark.parametrize(
    "status,api,final",
    [
        ("queued", "PENDING", False),
        ("running", "RUNNING", False),
        ("paused", "PAUSED", False),
        ("failed", "ERROR", True),
        ("completed", "COMPLETED", True),
        ("cancelled", "CANCELLED", True),
    ],
)
def test_ticket_controls_poll_finality_without_discarding_attempt(harness, status, api, final):
    harness.store._jobs["r"]["status"] = status
    response = harness.client.get("/agents/test/runs/r", params={"session_id": "s"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == api
    assert body["content"] == "attempt failed"
    assert body["metadata"]["retryable"] is True
    assert body["metadata"]["queue"] == {
        "status": status,
        "attempt": 1,
        "max_attempts": 3,
        "final": final,
        "run_status": "ERROR",
    }
    assert harness.db.get_session("s").runs[0].status == RunStatus.error, "poll must not mutate persisted state"


def test_exhausted_budget_and_permanent_failure_are_final(harness):
    harness.store._jobs["r"].update(status="failed", attempt=3)
    body = harness.client.get("/agents/test/runs/r", params={"session_id": "s"}).json()
    assert body["metadata"]["queue"]["final"] is True
    assert body["metadata"]["queue"]["attempt"] == 3
    # Permanent failure can settle early; remaining budget is not evidence of a retry.
    harness.store._jobs["r"]["attempt"] = 1
    harness.run.metadata = {"retryable": False}
    harness.db.upsert_run(harness.run, "s", user_id="owner")
    body = harness.client.get("/agents/test/runs/r", params={"session_id": "s"}).json()
    assert body["metadata"]["queue"]["final"] is True
    assert body["metadata"]["retryable"] is False


def test_store_failure_is_503_not_a_false_terminal_response(harness, monkeypatch):
    monkeypatch.setattr(harness.store, "get_job", AsyncMock(side_effect=OSError("offline")))
    response = harness.client.get("/agents/test/runs/r", params={"session_id": "s"})
    assert response.status_code == 503, response.text
    assert "finality" in response.json()["detail"]


def test_missing_ticket_finality_is_unknown(harness):
    harness.store._jobs.clear()
    body = harness.client.get("/agents/test/runs/r", params={"session_id": "s"}).json()
    assert body["metadata"]["queue"]["final"] is None
    assert body["metadata"]["queue"]["status"] == "unknown"


def test_poll_does_not_leak_other_users_ticket(harness):
    response = harness.client.get("/agents/test/runs/r", params={"session_id": "s"}, headers={"x-test-user": "other"})
    assert response.status_code == 404, response.text


def test_ticket_before_run_row_has_the_same_finality_contract(harness):
    harness.db.delete_session("s")
    body = harness.client.get("/agents/test/runs/r", params={"session_id": "s"}).json()
    assert body["status"] == "PENDING"
    assert body["metadata"]["queue"]["final"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("retryable", [False, True])
async def test_stream_error_marks_attempt_and_defers_finality(monkeypatch, retryable):
    import agno.os.event_streams as es
    from agno.os.event_streams import InMemoryEventStream
    from agno.os.managers import EventsBuffer, SSESubscriberManager

    stream = InMemoryEventStream(events_buffer=EventsBuffer(), subscriber_manager=SSESubscriberManager())
    monkeypatch.setattr(es, "_event_stream", stream)
    event = RunErrorEvent(run_id="r", content="failed", additional_data={"retryable": retryable})
    output = RunOutput(run_id="r", status=RunStatus.error, metadata={"retryable": retryable})

    class Component:
        async def arun(self, **kwargs):
            yield event
            yield output

    worker = QueueWorker(
        store=InMemoryQueueStore(), resolve_component=lambda *_: None, config=QueueConfig(durable=True)
    )
    job = QueuedJob(
        id="r", component_type="agent", component_id="test", session_id="s", payload={"stream": True}, max_attempts=2
    ).to_dict()
    job["attempt"] = 1
    assert await worker._execute_streaming(Component(), job) is output
    assert event.additional_data == {"retryable": retryable, "queue": {"attempt": 1, "max_attempts": 2, "final": None}}
    # The permanent-error stream can end, but ticket settlement remains the finality authority.
    expected = RunStatus.running if retryable else RunStatus.error
    assert await stream.get_run_status("r") == expected
