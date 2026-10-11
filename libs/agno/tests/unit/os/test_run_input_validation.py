"""Reject malformed run inputs before dispatch, including streaming/background requests."""

import json
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent
from agno.os import AgentOS
from agno.os.utils import get_request_kwargs


@pytest.fixture(params=[ClaudeAgent, CodexAgent])
def harness_client(request, monkeypatch):
    agent = request.param(id="test-inputs")
    run = AsyncMock(side_effect=AssertionError("Invalid input reached the harness"))
    monkeypatch.setattr(agent, "arun", run)
    app = AgentOS(agents=[agent]).get_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, run


@pytest.mark.parametrize("mode", [{"stream": "false"}, {"stream": "true"}, {"background": "true"}])
@pytest.mark.parametrize("field", ["images", "audio", "videos", "input_files"])
@pytest.mark.parametrize("value", ["not json", "123", "[1,2]", "null", "{}", ""])
def test_invalid_media_rejected_before_dispatch(harness_client, mode, field, value):
    client, run = harness_client
    response = client.post("/agents/test-inputs/runs", data={"message": "hi", field: value, **mode})
    assert response.status_code == 422, response.text
    assert field in response.json()["detail"]
    run.assert_not_called()


@pytest.mark.parametrize("value", ["{not json", "123", "null", "[]", '{"type":"string"}', ""])
@pytest.mark.parametrize("raw_schema", ["true", "false"])
def test_invalid_schema_rejected_before_dispatch(harness_client, value, raw_schema):
    client, run = harness_client
    response = client.post(
        "/agents/test-inputs/runs",
        data={"message": "hi", "stream": "false", "output_schema": value, "use_json_schema": raw_schema},
    )
    assert response.status_code == 422, response.text
    assert "output_schema" in response.json()["detail"]
    run.assert_not_called()


@pytest.fixture
def parser_client():
    app = FastAPI()

    @app.post("/parse")
    async def parse(request: Request):
        kwargs = await get_request_kwargs(request, parse)
        schema = kwargs.pop("output_schema", None)
        return {
            "media": {key: [item.to_dict() for item in value] for key, value in kwargs.items()},
            "schema": schema if isinstance(schema, dict) else schema.model_json_schema() if schema else None,
        }

    return TestClient(app)


@pytest.mark.parametrize("field", ["images", "audio", "videos", "input_files"])
def test_empty_media_array_is_valid(parser_client, field):
    response = parser_client.post("/parse", data={field: "[]"})
    assert response.status_code == 200
    assert response.json()["media"]["files" if field == "input_files" else field] == []


def test_valid_media_retains_bytes_but_drops_untrusted_storage_reference(parser_client):
    from agno.media import Image

    image = Image(content=b"image bytes", mime_type="image/png").to_dict()
    image["media_reference"] = {"storage_key": "another-users-file"}
    response = parser_client.post("/parse", data={"images": json.dumps([image])})
    assert response.status_code == 200
    reconstructed = response.json()["media"]["images"][0]
    assert reconstructed["content"] == image["content"]
    assert not reconstructed.get("media_reference")


@pytest.mark.parametrize("raw_schema", ["true", "false"])
def test_valid_object_schema_preserves_required_field(parser_client, raw_schema):
    schema = {"type": "object", "properties": {"answer": {"type": "integer"}}, "required": ["answer"]}
    response = parser_client.post("/parse", data={"output_schema": json.dumps(schema), "use_json_schema": raw_schema})
    assert response.status_code == 200
    assert response.json()["schema"]["properties"]["answer"]["type"] == "integer"
    assert response.json()["schema"]["required"] == ["answer"]


def test_bad_media_item_does_not_silently_disappear(parser_client):
    response = parser_client.post("/parse", data={"images": '[{"url":123}]'})
    assert response.status_code == 422
    assert "reconstruct" in response.json()["detail"]
