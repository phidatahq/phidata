"""Expected admission conflicts must not enter ASGI's unhandled-error path."""

import socket
import threading
import time
from contextlib import contextmanager
from unittest.mock import AsyncMock

import httpx
import pytest
import uvicorn
from fastapi import FastAPI

from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent
from agno.db.in_memory import InMemoryDb
from agno.exceptions import SessionBusyError
from agno.os import AgentOS
from agno.run.agent import RunOutput


@contextmanager
def live_server(app):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, http="h11", loop="asyncio", lifespan="off", log_level="error"))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and worker.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            assert not worker.is_alive()


@pytest.mark.parametrize("agent_type,continuation", [(ClaudeAgent, False), (CodexAgent, False), (ClaudeAgent, True)])
@pytest.mark.parametrize("background", [False, True])
@pytest.mark.parametrize("custom_app", [False, True])
def test_busy_response_preserves_pooled_connection(agent_type, background, continuation, custom_app, monkeypatch):
    agent = agent_type(id="busy-agent", db=InMemoryDb())
    run = AsyncMock(side_effect=SessionBusyError("Session already active", session_id="session"))
    monkeypatch.setattr(agent, "acontinue_run" if continuation else "arun", run)
    monkeypatch.setattr(agent, "aget_run_output", AsyncMock(return_value=RunOutput(run_id="original")))
    app = AgentOS(agents=[agent], base_app=FastAPI() if custom_app else None).get_app()
    with live_server(app) as url, httpx.Client(base_url=url, limits=httpx.Limits(max_connections=1)) as client:
        response = client.post(
            "/agents/busy-agent/runs/original/continue" if continuation else "/agents/busy-agent/runs",
            data={"message": "next", "session_id": "session", "stream": "false", "background": str(background).lower()},
        )
        assert response.status_code == 409, response.text
        if not custom_app:
            assert response.json()["error_type"] == "session_busy"
        health = client.get("/health")
        assert health.status_code == 200
        # A reconnect is not a pass: both responses must use the same TCP stream.
        assert health.extensions["network_stream"] is response.extensions["network_stream"]
    run.assert_awaited_once()
