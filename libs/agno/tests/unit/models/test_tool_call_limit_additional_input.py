"""RetryAgentRun / StopAgentRun messages must not be charged against tool_call_limit."""

import json
from typing import Any

from agno.exceptions import RetryAgentRun
from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse
from agno.tools.function import Function


class _LoopingModel(Model):
    def __init__(self):
        super().__init__(id="t", name="t", provider="test")
        self.calls = 0

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        self.calls += 1
        if self.calls > 20:
            return ModelResponse(role="assistant", content="done")
        return ModelResponse(
            role="assistant",
            tool_calls=[
                {
                    "id": f"c{self.calls}",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": json.dumps({"query": f"q{self.calls}"})},
                }
            ],
        )

    async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self.invoke()

    def invoke_stream(self, *args: Any, **kwargs: Any):
        yield self.invoke()

    async def ainvoke_stream(self, *args: Any, **kwargs: Any):
        yield self.invoke()

    def _parse_provider_response(self, response: Any, **kwargs: Any) -> ModelResponse:
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return response


def _make_tool(runs: list):
    def lookup(query: str) -> str:
        """Look something up."""
        runs.append(query)
        if len(runs) == 1:
            raise RetryAgentRun(
                "bad query",
                user_message="Please retry with a different query.",
                messages=[Message(role="assistant", content="a"), Message(role="user", content="b")],
            )
        return "ok"

    return Function.from_callable(lookup)


def test_limit_charge_ignores_attached_messages():
    model = _LoopingModel()
    results = [
        Message(role="tool", content="x", tool_call_id="1", tool_name="lookup"),
        Message(role="user", content="retry"),
        Message(role="assistant", content="hint"),
    ]
    assert model._limit_charge_for(results, None) == 1


def test_response_runs_full_tool_call_limit_after_retry_with_messages():
    runs: list = []
    model = _LoopingModel()
    model.response(
        messages=[Message(role="user", content="go")],
        tools=[_make_tool(runs)],
        tool_call_limit=3,
    )
    assert len(runs) == 3
