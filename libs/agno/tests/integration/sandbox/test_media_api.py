"""Bounded inputs survive durable admission and replacement of actual Docker compute."""

import base64
import json

import pytest

from agno.media import File
from agno.os.job_queue import aprepare_queued_run
from agno.sandbox.artifacts import SandboxArtifacts
from tests.integration.sandbox.test_agentos import IMAGE, REDIS, URL, settled
from tests.integration.sandbox.test_agentos import service as _service_fixture

service = _service_fixture
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not URL or not IMAGE or not REDIS, reason="Enable dedicated local sandbox services"),
]


async def test_upload_and_replacement_retain_exact_bytes(service):
    client, agent, _, handles = service
    data = {"message": "edit attached file", "session_id": "session", "stream": "false"}
    content = b"print('hello')\n"
    response = await client.post(
        "/agents/coder/runs", data=data, files={"files": ("source.txt", content, "text/plain")}
    )
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["status"] == "COMPLETED", first
    stored = await agent.aget_run_output(first["run_id"], "session")
    assert stored.input.files[0].get_content_bytes() == content
    artifacts = SandboxArtifacts(agent.coordinator.store, agent.coordinator.transfer.store)
    listing = await artifacts.alist(agent_id="coder", session_id="session", user_id=None)
    path = next(value["path"] for value in listing["files"] if value["path"].endswith("source.txt"))
    assert (await artifacts.aread(path, agent_id="coder", session_id="session", user_id=None)).content == content
    second = await client.post("/agents/coder/runs", data={**data, "message": "continue"})
    assert second.json()["status"] == "COMPLETED", second.text
    assert len(handles) == 2 and handles[0].provider_ref != handles[1].provider_ref
    assert (await artifacts.aread(path, agent_id="coder", session_id="session", user_id=None)).content == content


async def test_json_image_file_idempotency_and_background_input(service):
    client, agent, app, _ = service
    data = {
        "message": "inspect",
        "session_id": "session",
        "stream": "false",
        "background": "true",
        "images": json.dumps([{"content": base64.b64encode(b"image-fixture").decode(), "format": "png"}]),
        "input_files": json.dumps([{"content": "YWJj", "filename": "input.txt"}]),
    }
    first = await client.post("/agents/coder/runs", data=data, headers={"Idempotency-Key": "media"})
    assert first.status_code == 202, first.text
    second = await client.post("/agents/coder/runs", data=data, headers={"Idempotency-Key": "media"})
    assert second.status_code == 202 and first.json()["run_id"] == second.json()["run_id"], second.text
    job = await settled(app, first.json()["run_id"])
    assert job["status"] == "completed", job
    stored = await agent.aget_run_output(job["id"], "session")
    assert stored.input.images[0].get_content_bytes() == b"image-fixture"
    assert stored.input.files[0].get_content_bytes() == b"abc"


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_files", [{"filepath": "/etc/passwd", "content": "YQ=="}]),
        ("input_files", [{"content": "bad!"}]),
        ("audio", [{"content": "YQ=="}]),
        ("sandbox_media", []),
        ("input_files", None),
        ("input_files", {}),
    ],
)
async def test_http_rejects_unsupported_media_before_allocation(service, field, value):
    client, _, _, handles = service
    response = await client.post(
        "/agents/coder/runs",
        data={"message": "bad", "session_id": "session", "stream": "false", field: json.dumps(value)},
    )
    assert response.status_code == 400, response.text
    assert handles == []


async def test_worker_preparation_can_reconstruct_bytes_without_http_process(service):
    _, agent, _, _ = service
    options = agent._media_kwargs(files=[File(content=b"worker recovery", filename="recovery.txt")])
    await aprepare_queued_run(agent, "agent", "recovered", "session", None, "continue", run_kwargs=options)
    prepared = await agent.aget_run_output("recovered", "session")
    assert prepared.input.files[0].get_content_bytes() == b"worker recovery"
    result = await agent.arun("continue", run_id="recovered", session_id="session", **options)
    assert result.status == "COMPLETED", result
    assert result.input.files[0].get_content_bytes() == b"worker recovery"
