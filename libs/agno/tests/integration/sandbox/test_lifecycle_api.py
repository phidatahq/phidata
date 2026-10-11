import asyncio

import pytest

from tests.integration.sandbox.test_agentos import IMAGE, REDIS, URL, settled
from tests.integration.sandbox.test_agentos import service as _service_fixture

service = _service_fixture
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not URL or not IMAGE or not REDIS, reason="Enable dedicated local services"),
]


async def test_purge_before_conversation_delete_and_reject_future_submission(service):
    client, agent, _, handles = service
    response = await client.post(
        "/agents/coder/runs", data={"message": "keep conversation", "session_id": "session", "stream": "false"}
    )
    assert response.status_code == 200 and response.json()["status"] == "COMPLETED", response.text
    refused = await client.delete("/sessions/session")
    assert refused.status_code == 409, refused.text
    purge = await client.delete("/agents/coder/sessions/session/sandbox/recovery")
    assert purge.status_code == 200 and purge.json()["conversation_retained"], purge.text
    assert (await agent.aget_session("session")).runs
    assert (await client.get("/agents/coder/sessions/session/sandbox/artifacts")).status_code == 404
    future = await client.post(
        "/agents/coder/runs", data={"message": "no", "session_id": "session", "stream": "false", "background": "true"}
    )
    assert future.status_code == 400 and "retired" in future.text
    assert len(handles) == 1
    assert (await client.delete("/sessions/session")).status_code == 204
    assert await agent.aget_session("session") is None


async def test_api_retirement_preserves_last_checkpoint(service):
    client, agent, app, handles = service
    first = await client.post(
        "/agents/coder/runs", data={"message": "first", "session_id": "session", "stream": "false"}
    )
    agent.runtime_config = {"delay": 10}
    second = await client.post(
        "/agents/coder/runs",
        data={"message": "second", "session_id": "session", "stream": "false", "background": "true"},
    )
    run_id = second.json()["run_id"]

    async def allocated():
        while len(handles) < 2:
            await asyncio.sleep(0.05)

    await asyncio.wait_for(allocated(), 10)
    refused = await client.delete("/agents/coder/sessions/session/sandbox/recovery")
    assert refused.status_code == 409
    retire = await client.post("/agents/coder/sessions/session/sandbox/retire")
    assert retire.status_code == 200 and retire.json()["recovery_preserved"], retire.text
    assert (await settled(app, run_id))["status"] == "cancelled"
    download = await client.get(
        "/agents/coder/sessions/session/sandbox/artifact", params={"path": "fixture-effects.txt"}
    )
    assert download.status_code == 200 and download.text == first.json()["run_id"] + "\n"


async def test_accepted_submission_racing_deletion_fails_without_allocation(service, monkeypatch):
    from agno.sandbox.lifecycle import SandboxLifecycle

    client, agent, app, handles = service
    first = await client.post(
        "/agents/coder/runs", data={"message": "first", "session_id": "session", "stream": "false"}
    )
    assert first.status_code == 200
    check = agent.coordinator.store._acheck_acceptance

    async def delete_after_check(agent_id, session_id, user_id):
        await check(agent_id, session_id, user_id)
        await SandboxLifecycle(agent.coordinator).adelete_recovery(
            agent_id=agent_id, session_id=session_id, user_id=user_id
        )

    monkeypatch.setattr(agent.coordinator.store, "_acheck_acceptance", delete_after_check)
    accepted = await client.post(
        "/agents/coder/runs",
        data={"message": "racing", "session_id": "session", "stream": "false", "background": "true"},
    )
    assert accepted.status_code == 202, accepted.text
    job = await settled(app, accepted.json()["run_id"])
    assert job["status"] == "failed" and job["attempt"] == 1, job
    assert len(handles) == 1


async def test_http_mutations_require_session_owner(service):
    import httpx

    client, agent, app, _ = service
    first = await client.post(
        "/agents/coder/runs", data={"message": "owned", "session_id": "session", "user_id": "owner", "stream": "false"}
    )
    assert first.status_code == 200

    async def scoped(scope, receive, send):
        scope.setdefault("state", {}).update(user_id="attacker", user_isolation_enabled=True)
        await app(scope, receive, send)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=scoped), base_url="http://test") as attacker:
        assert (await attacker.post("/agents/coder/sessions/session/sandbox/retire")).status_code == 404
        assert (await attacker.delete("/agents/coder/sessions/session/sandbox/recovery")).status_code == 404
    assert (
        await client.get("/agents/coder/sessions/session/sandbox/artifact", params={"path": "fixture-effects.txt"})
    ).status_code == 200
