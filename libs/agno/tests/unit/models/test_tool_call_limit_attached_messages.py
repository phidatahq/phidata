"""Messages attached to RetryAgentRun / StopAgentRun (user_message, agent_message,
messages) are added to the tool results, but they are not tool calls and must not
be charged against tool_call_limit on any of the four response paths."""

import json
from typing import Any, AsyncIterator, Iterator, List

import pytest

from agno.exceptions import RetryAgentRun
from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse
from agno.tools.function import Function

TOOL_CALL_LIMIT = 3


class _LoopingModel(Model):
    """Asks for one `lookup` tool call per turn until the run stops it."""

    def __init__(self):
        super().__init__(id="stub", name="stub", provider="stub")
        self.turns = 0

    def _next(self) -> ModelResponse:
        self.turns += 1
        if self.turns > 20:
            return ModelResponse(role="assistant", content="done")
        return ModelResponse(
            role="assistant",
            tool_calls=[
                {
                    "id": f"call_{self.turns}",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": json.dumps({"query": f"q{self.turns}"})},
                }
            ],
        )

    def invoke(self, *args, **kwargs) -> ModelResponse:
        return self._next()

    async def ainvoke(self, *args, **kwargs) -> ModelResponse:
        return self._next()

    def invoke_stream(self, *args, **kwargs) -> Iterator[ModelResponse]:
        yield self._next()

    async def ainvoke_stream(self, *args, **kwargs) -> AsyncIterator[ModelResponse]:
        yield self._next()

    def _parse_provider_response(self, response: Any, **kwargs) -> ModelResponse:
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return response


def _lookup_tool(retry_kwargs: dict, runs: List[str]) -> Function:
    def lookup(query: str) -> str:
        """Look something up."""
        runs.append(query)
        if len(runs) == 1:
            raise RetryAgentRun("bad query", **retry_kwargs)
        return "ok"

    return Function.from_callable(lookup)


# Factories, so each test gets fresh Message objects.
RETRY_CASES = {
    "no_messages": dict,
    "user_message": lambda: {"user_message": "Please retry with a different query."},
    "agent_message": lambda: {"agent_message": "I will try a different query."},
    "user_message_and_messages": lambda: {
        "user_message": "Please retry with a different query.",
        "messages": [
            Message(role="user", content="Extra context one."),
            {"role": "assistant", "content": "Extra context two."},
        ],
    },
}


def _run(path: str, model: Model, tool: Function) -> None:
    messages = [Message(role="user", content="go")]
    if path == "response":
        model.response(messages=messages, tools=[tool], tool_call_limit=TOOL_CALL_LIMIT)
    elif path == "response_stream":
        for _ in model.response_stream(messages=messages, tools=[tool], tool_call_limit=TOOL_CALL_LIMIT):
            pass
    else:
        raise ValueError(path)


async def _arun(path: str, model: Model, tool: Function) -> None:
    messages = [Message(role="user", content="go")]
    if path == "aresponse":
        await model.aresponse(messages=messages, tools=[tool], tool_call_limit=TOOL_CALL_LIMIT)
    elif path == "aresponse_stream":
        async for _ in model.aresponse_stream(messages=messages, tools=[tool], tool_call_limit=TOOL_CALL_LIMIT):
            pass
    else:
        raise ValueError(path)


@pytest.mark.parametrize("retry_kwargs", RETRY_CASES.values(), ids=RETRY_CASES.keys())
@pytest.mark.parametrize("path", ["response", "response_stream"])
def test_retry_messages_not_charged_against_tool_call_limit(path: str, retry_kwargs):
    runs: List[str] = []
    _run(path, _LoopingModel(), _lookup_tool(retry_kwargs(), runs))
    assert len(runs) == TOOL_CALL_LIMIT


@pytest.mark.parametrize("retry_kwargs", RETRY_CASES.values(), ids=RETRY_CASES.keys())
@pytest.mark.parametrize("path", ["aresponse", "aresponse_stream"])
async def test_retry_messages_not_charged_against_tool_call_limit_async(path: str, retry_kwargs):
    runs: List[str] = []
    await _arun(path, _LoopingModel(), _lookup_tool(retry_kwargs(), runs))
    assert len(runs) == TOOL_CALL_LIMIT
