"""The compaction route's contract: a decline is a 200 with a status, a missing session is a 404."""

import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agno.agent import Agent
from agno.compaction import Compaction
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from agno.os.routers.agents.router import get_agent_router
from agno.session import AgentSession


def _client(authorization: bool = False) -> TestClient:
    db = SqliteDb(db_file=str(Path(tempfile.mkdtemp()) / "compaction.db"))
    db.upsert_session(AgentSession(session_id="s1", agent_id="a1", runs=[]))
    db.upsert_session(AgentSession(session_id="s2", agent_id="a2", runs=[]))
    agents = [Agent(id=agent_id, db=db, compaction=Compaction()) for agent_id in ("a1", "a2")]
    app = FastAPI()
    if authorization:

        @app.middleware("http")
        async def enable_authorization(request, call_next):
            request.state.authorization_enabled = True
            return await call_next(request)

    app.include_router(get_agent_router(AgentOS(agents=agents)))
    return TestClient(app)


@pytest.fixture
def client() -> TestClient:
    return _client()


def test_route_is_registered():
    db = SqliteDb(db_file=str(Path(tempfile.mkdtemp()) / "compaction.db"))
    agent_os = AgentOS(agents=[Agent(id="a1", db=db, compaction=Compaction())])

    paths = {(route.path, tuple(sorted(route.methods))) for route in get_agent_router(agent_os).routes}

    assert ("/agents/{agent_id}/sessions/{session_id}/compact", ("POST",)) in paths


def test_decline_is_a_200_with_a_reason(client: TestClient):
    """Declining to fold is a normal outcome, so a UI must not have to treat it as an error.

    Raising would make "folding would not help here" indistinguishable from a failure.
    """
    response = client.post("/agents/a1/sessions/s1/compact")

    assert response.status_code == 200
    body = response.json()
    assert body["compacted"] is False
    assert body["status"] == "no_history"
    assert body["message"]  # always something displayable
    assert body["record"] is None


def test_unknown_session_is_a_404(client: TestClient):
    """A session that does not exist is a 404, as on the other session routes - not no_history,
    which would read as "exists, nothing to fold yet"."""
    response = client.post("/agents/a1/sessions/does-not-exist/compact")

    assert response.status_code == 404


def test_another_agents_session_is_a_404(monkeypatch):
    """The resource gate authorised a1, so a1's route must not fold a2's session."""

    async def may_run_a1_only(request, resource_id, resource_type, action):
        return resource_id == "a1"

    monkeypatch.setattr("agno.os.auth.acheck_resource_access", may_run_a1_only)
    client = _client(authorization=True)

    assert client.post("/agents/a1/sessions/s1/compact").status_code == 200
    response = client.post("/agents/a1/sessions/s2/compact")

    assert response.status_code == 404


def test_unknown_agent_is_a_404(client: TestClient):
    """A missing agent IS an error - it means the caller asked for something that does not exist."""
    response = client.post("/agents/nope/sessions/s1/compact")

    assert response.status_code == 404


def test_response_shape_is_stable(client: TestClient):
    """These keys are the contract the FE renders; adding is safe, renaming is not."""
    body = client.post("/agents/a1/sessions/s1/compact").json()

    assert set(body) == {"status", "message", "compacted", "record", "metrics"}


@pytest.fixture(params=["claude", "codex"])
def external_compaction(request, monkeypatch):
    from unittest.mock import AsyncMock

    from agno.agents.claude import ClaudeAgent
    from agno.agents.codex import CodexAgent
    from agno.db.in_memory import InMemoryDb

    db = InMemoryDb()
    db.upsert_session(AgentSession(session_id="s1", agent_id="external", user_id="owner", runs=[]))
    db.upsert_session(AgentSession(session_id="other", agent_id="different", user_id="owner", runs=[]))
    cls = ClaudeAgent if request.param == "claude" else CodexAgent
    agent = cls(id="external", db=db)
    run = AsyncMock(side_effect=AssertionError("Compaction must not execute a model turn"))
    monkeypatch.setattr(agent, "arun", run)
    app = AgentOS(agents=[agent]).get_app()

    @app.middleware("http")
    async def scope(request, call_next):
        request.state.user_id = request.headers.get("x-test-user", "owner")
        request.state.user_isolation_enabled = True
        return await call_next(request)

    with TestClient(app, raise_server_exceptions=False) as client:
        yield request.param, agent, client, run
    run.assert_not_called()


def test_external_missing_session_is_404_before_capability_check(external_compaction):
    _, _, client, _ = external_compaction
    response = client.post("/agents/external/sessions/missing/compact")
    assert response.status_code == 404, response.text


def test_external_compaction_cannot_access_other_users_session(external_compaction):
    _, _, client, _ = external_compaction
    response = client.post("/agents/external/sessions/s1/compact", headers={"x-test-user": "stranger"})
    assert response.status_code == 404, response.text


def test_external_compaction_other_component_is_404(external_compaction):
    _, _, client, _ = external_compaction
    response = client.post("/agents/external/sessions/other/compact")
    assert response.status_code == 404, response.text


def test_claude_http_compaction_is_explicitly_unsupported(external_compaction):
    provider, _, client, _ = external_compaction
    if provider != "claude":
        pytest.skip("Claude capability contract")
    response = client.post("/agents/external/sessions/s1/compact")
    assert response.status_code == 501, response.text
    assert "/compact as a run input" in response.json()["detail"]


@pytest.mark.parametrize("result", [True, False])
def test_codex_http_compaction_serializes_native_result(external_compaction, monkeypatch, result):
    from unittest.mock import AsyncMock

    provider, agent, client, _ = external_compaction
    if provider != "codex":
        pytest.skip("Codex capability contract")
    compact = AsyncMock(return_value=result)
    monkeypatch.setattr(agent, "acompact", compact)
    response = client.post("/agents/external/sessions/s1/compact")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["compacted"] is result
    assert body["status"] == ("compacted" if result else "no_history")
    assert body["record"] is None and body["metrics"] is None
    compact.assert_awaited_once_with(session_id="s1", user_id="owner")


@pytest.mark.parametrize("failure,code", [("busy", 409), ("timeout", 504)])
def test_codex_http_compaction_errors_are_handled(external_compaction, monkeypatch, failure, code):
    from unittest.mock import AsyncMock

    from agno.exceptions import SessionBusyError

    provider, agent, client, _ = external_compaction
    if provider != "codex":
        pytest.skip("Codex capability contract")
    error = SessionBusyError("run is active", session_id="s1") if failure == "busy" else TimeoutError("native timeout")
    monkeypatch.setattr(agent, "acompact", AsyncMock(side_effect=error))
    response = client.post("/agents/external/sessions/s1/compact")
    assert response.status_code == code, response.text
