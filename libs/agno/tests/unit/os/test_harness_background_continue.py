"""Never execute a requested background checkpoint continuation inline."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from agno.agents.claude import ClaudeAgent
from agno.db.in_memory import InMemoryDb
from agno.db.schemas.jobs import QueuedJob
from agno.job_queue.config import QueueConfig
from agno.job_queue.store import InMemoryQueueStore
from agno.os import AgentOS
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from agno.session import AgentSession


@pytest.fixture
def harness(monkeypatch):
    db = InMemoryDb()
    run = RunOutput(run_id="original", session_id="s1", agent_id="claude", status=RunStatus.completed, content="answer")
    db.upsert_session(AgentSession(session_id="s1", agent_id="claude", user_id="owner", runs=[run]))
    agent = ClaudeAgent(id="claude", db=db)
    continuation = AsyncMock(side_effect=AssertionError("Unsupported background request executed"))
    monkeypatch.setattr(agent, "acontinue_run", continuation)
    app = AgentOS(agents=[agent], telemetry=False).get_app()

    @app.middleware("http")
    async def scope(request, call_next):
        request.state.user_id = request.headers.get("x-test-user", "owner")
        request.state.user_isolation_enabled = True
        return await call_next(request)

    # Do not run app lifespan: these tests own the queue and never launch workers.
    return SimpleNamespace(agent=agent, db=db, run=run, app=app, client=TestClient(app), continuation=continuation)


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("option", [{}, {"fork": "true"}, {"regenerate": "true"}])
@pytest.mark.parametrize("queued", [False, True])
def test_background_checkpoint_does_not_execute_or_mutate(harness, stream, option, queued):
    store = InMemoryQueueStore()
    if queued:
        harness.app.state.queue_worker = SimpleNamespace(store=store, config=QueueConfig(durable=True))
    before = harness.db.get_session("s1").to_dict()
    response = harness.client.post(
        "/agents/claude/runs/original/continue",
        data={"background": "true", "stream": str(stream).lower(), "session_id": "s1", "input": "next", **option},
    )
    assert response.status_code == 501, response.text
    assert "no continuation was started" in response.json()["detail"]
    harness.continuation.assert_not_called()
    assert harness.db.get_session("s1").to_dict() == before
    assert not store._jobs


def test_background_continuation_missing_run_is_404(harness):
    response = harness.client.post(
        "/agents/claude/runs/missing/continue", data={"background": "true", "session_id": "s1"}
    )
    assert response.status_code == 404, response.text
    harness.continuation.assert_not_called()


def test_background_continuation_checks_owner_before_capability(harness):
    response = harness.client.post(
        "/agents/claude/runs/original/continue",
        data={"background": "true", "session_id": "s1"},
        headers={"x-test-user": "other"},
    )
    assert response.status_code == 404, response.text
    harness.continuation.assert_not_called()


def test_foreground_checkpoint_still_dispatches(harness):
    harness.continuation.side_effect = None
    harness.continuation.return_value = RunOutput(
        run_id="forked", session_id="s1", agent_id="claude", status=RunStatus.completed, content="next answer"
    )
    response = harness.client.post(
        "/agents/claude/runs/original/continue",
        data={"background": "false", "stream": "false", "session_id": "s1", "fork": "true"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["run_id"] == "forked"
    harness.continuation.assert_awaited_once()


def test_existing_paused_durable_ticket_is_still_accepted(harness):
    harness.run.status = RunStatus.paused
    harness.db.upsert_run(harness.run, session_id="s1", user_id="owner")
    store = InMemoryQueueStore()
    store._jobs["original"] = QueuedJob(
        id="original", component_type="agent", component_id="claude", session_id="s1", user_id="owner", payload={}
    ).to_dict()
    store._jobs["original"]["status"] = "paused"
    harness.app.state.queue_worker = SimpleNamespace(store=store, config=QueueConfig(durable=True))
    response = harness.client.post(
        "/agents/claude/runs/original/continue",
        data={"background": "true", "stream": "false", "session_id": "s1", "input": "approval"},
    )
    assert response.status_code == 202, response.text
    assert response.json()["run_id"] == "original"
    assert store._jobs["original"]["status"] == "queued"
    assert store._jobs["original"]["payload"]["continue"]["input"] == "approval"
    harness.continuation.assert_not_called()
