"""Harness output validation preserves evidence and never reports false completion."""

from copy import deepcopy

import pytest
from pydantic import BaseModel, Field

from agno.agents.base import ExternalRunResult, ExternalRunStructuredOutputEvent
from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent
from agno.db.sqlite import SqliteDb
from agno.models.response import ToolExecution
from agno.run.agent import RunContentEvent, RunOutput, ToolCallCompletedEvent
from agno.run.base import RunStatus


class Answer(BaseModel):
    count: int = Field(ge=1)


SCHEMA = {
    "type": "object",
    "properties": {"count": {"type": "integer", "minimum": 1}},
    "required": ["count"],
    "additionalProperties": False,
}


@pytest.fixture(params=[ClaudeAgent, CodexAgent])
def agent(request, tmp_path):
    return request.param(id="validated", db=SqliteDb(db_file=str(tmp_path / "runs.db")), store_events=True, retries=2)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["sync", "async", "sync-stream", "async-stream"])
@pytest.mark.parametrize("schema", [Answer, SCHEMA])
@pytest.mark.parametrize("answer", [None, {"wrong": "value"}, {"count": 0}, {"count": 2}])
async def test_validation_is_terminal_and_preserves_tools(agent, mode, schema, answer, monkeypatch):
    calls = []
    tool = ToolExecution(tool_call_id="receipt", tool_name="mutate", result="effect committed")

    async def run(input, **kwargs):
        calls.append(kwargs)
        return ExternalRunResult(content="raw answer", structured_output=answer, tools=[tool])

    async def stream(input, **kwargs):
        calls.append(kwargs)
        yield ToolCallCompletedEvent(tool=tool, run_id=kwargs["run_id"])
        yield RunContentEvent(content="raw answer", run_id=kwargs["run_id"])
        yield ExternalRunStructuredOutputEvent(structured_output=answer)

    monkeypatch.setattr(agent, "_arun_adapter", run)
    monkeypatch.setattr(agent, "_arun_adapter_stream", stream)
    kwargs = {"session_id": "s", "output_schema": deepcopy(schema)}
    events = []
    if mode == "sync":
        result = agent.run("apply", **kwargs)
    elif mode == "async":
        result = await agent.arun("apply", **kwargs)
    elif mode == "sync-stream":
        events = list(agent.run("apply", stream=True, yield_run_output=True, **kwargs))
        result = events[-1]
    else:
        events = [event async for event in agent.arun("apply", stream=True, yield_run_output=True, **kwargs)]
        result = events[-1]
    assert isinstance(result, RunOutput)
    assert len(calls) == 1
    assert len(result.tools) == 1 and result.tools[0].result == "effect committed"
    valid = answer == {"count": 2}
    assert result.status == (RunStatus.completed if valid else RunStatus.error)
    saved = await agent.aget_run_output(result.run_id, session_id="s")
    assert saved.status == result.status
    assert saved.tools[0].tool_call_id == "receipt"
    if not valid:
        assert result.content == "raw answer"
        assert result.metadata["retryable"] is False
        assert result.metadata["error_type"] == "output_validation_error"
        assert saved.metadata["output_validation_error"]
        if events:
            assert not any(getattr(event, "event", None) == "RunCompleted" for event in events)
            terminal = events[-2]
            assert terminal.event == "RunError"
            assert terminal.error_type == "output_validation_error"
            assert terminal.additional_data["retryable"] is False


def test_local_references_and_constraints_are_validated(agent, monkeypatch):
    schema = {
        "type": "object",
        "properties": {"count": {"$ref": "#/$defs/count"}},
        "required": ["count"],
        "$defs": {"count": {"type": "integer", "minimum": 1}},
    }

    async def run(input, **kwargs):
        return ExternalRunResult(content='{"count":0}')

    monkeypatch.setattr(agent, "_arun_adapter", run)
    result = agent.run("answer", output_schema=schema)
    assert result.status == RunStatus.error


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "properties": {"count": {"type": "nonexistent"}}},
        {"type": "object", "properties": {"count": {"$ref": "https://example.com/schema.json"}}},
    ],
)
def test_invalid_or_external_schema_rejected_before_execution(agent, monkeypatch, schema):
    from unittest.mock import AsyncMock

    from jsonschema.exceptions import SchemaError

    run = AsyncMock()
    monkeypatch.setattr(agent, "_arun_adapter", run)
    with pytest.raises((ValueError, SchemaError)):
        agent.run("answer", output_schema=schema)
    run.assert_not_called()


def test_reference_named_property_in_enum_is_literal_data():
    from agno.utils.output_schema import output_validator

    value = {"$ref": "https://example.com/literal"}
    validator = output_validator({"type": "object", "enum": [value]})
    validator.validate(value)


def test_unresolved_local_reference_is_rejected_before_execution(agent, monkeypatch):
    from unittest.mock import AsyncMock

    run = AsyncMock()
    monkeypatch.setattr(agent, "_arun_adapter", run)
    schema = {"type": "object", "properties": {"count": {"$ref": "#/$defs/missing"}}}
    with pytest.raises(ValueError, match="unresolved local reference"):
        agent.run("answer", output_schema=schema)
    run.assert_not_called()
