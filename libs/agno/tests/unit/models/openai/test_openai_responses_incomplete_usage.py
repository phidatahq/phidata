"""Usage metrics must survive a truncated Responses stream.

A generation cut short by max_output_tokens or a content filter ends on
response.incomplete, not response.completed. The incomplete event carries the
same usage envelope, so streaming metrics must not depend on which terminal
event arrived.
"""

from types import SimpleNamespace

from openai.types.responses import ResponseUsage

from agno.models.message import Message
from agno.models.openai.responses import OpenAIResponses


def _usage():
    return ResponseUsage.construct(
        input_tokens=11,
        output_tokens=5,
        total_tokens=16,
        input_tokens_details={"cached_tokens": 0},
        output_tokens_details={"reasoning_tokens": 0},
    )


def _feed(event_type, usage):
    event = SimpleNamespace(type=event_type, response=SimpleNamespace(usage=usage))
    model_response, tool_use = OpenAIResponses(api_key="test")._parse_provider_response_delta(
        event, Message(role="assistant"), {}
    )
    return model_response, tool_use


def test_incomplete_stream_reports_usage():
    model_response, tool_use = _feed("response.incomplete", _usage())
    assert tool_use == {}
    assert model_response.response_usage is not None
    assert model_response.response_usage.input_tokens == 11
    assert model_response.response_usage.total_tokens == 16


def test_completed_stream_still_reports_usage():
    model_response, _ = _feed("response.completed", _usage())
    assert model_response.response_usage is not None
    assert model_response.response_usage.total_tokens == 16


def test_incomplete_stream_without_usage_stays_none():
    model_response, _ = _feed("response.incomplete", None)
    assert model_response.response_usage is None
