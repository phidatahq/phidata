"""Messages attached to RetryAgentRun / StopAgentRun must not spend the tool call limit.

``Model._handle_agent_exception`` collects the messages attached to an
``AgentRunException`` (``user_message``, ``agent_message`` and ``messages``)
into ``additional_input``, and ``run_function_calls`` appends them to
``function_call_results`` next to the tool result itself. Only the tool
result may be charged against ``tool_call_limit``: with a limit of 3, a run
whose first tool call raises ``RetryAgentRun`` with attached messages must
still execute 3 tools.
"""

import json
from typing import Any, Callable, Dict, List, Optional

import pytest

from agno.exceptions import RetryAgentRun
from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse
from agno.tools.function import Function

TOOL_CALL_LIMIT = 3


class LoopingModel(Model):
    """Stub model that requests one ``lookup`` tool call per turn."""

    def __init__(self) -> None:
        super().__init__(id="test", name="test", provider="test")
        self.turn = 0

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        self.turn += 1
        if self.turn > 20:
            return ModelResponse(role="assistant", content="done")
        return ModelResponse(
            role="assistant",
            tool_calls=[
                {
                    "id": f"call-{self.turn}",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": json.dumps({"query": f"q{self.turn}"})},
                }
            ],
        )

    async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self.invoke(*args, **kwargs)

    def invoke_stream(self, *args: Any, **kwargs: Any):
        yield self.invoke(*args, **kwargs)

    async def ainvoke_stream(self, *args: Any, **kwargs: Any):
        yield self.invoke(*args, **kwargs)

    def _parse_provider_response(self, response: Any, **kwargs: Any) -> ModelResponse:
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return response


def make_lookup(executions: List[str], exception_kwargs: Dict[str, Any]) -> Callable[[str], str]:
    def lookup(query: str) -> str:
        """Look something up."""
        executions.append(query)
        if len(executions) == 1 and exception_kwargs is not None:
            raise RetryAgentRun("bad query", **exception_kwargs)
        return "ok"

    return lookup


def run_sync(entry_point: str, exception_kwargs: Optional[Dict[str, Any]]) -> int:
    executions: List[str] = []
    model = LoopingModel()
    tools = [Function.from_callable(make_lookup(executions, exception_kwargs or {}))]
    messages = [Message(role="user", content="go")]
    if entry_point == "response":
        model.response(messages=messages, tools=tools, tool_call_limit=TOOL_CALL_LIMIT)
    elif entry_point == "response_stream":
        for _ in model.response_stream(messages=messages, tools=tools, tool_call_limit=TOOL_CALL_LIMIT):
            pass
    else:
        raise ValueError(entry_point)
    return len(executions)


async def run_async(entry_point: str, exception_kwargs: Optional[Dict[str, Any]]) -> int:
    executions: List[str] = []
    model = LoopingModel()
    tools = [Function.from_callable(make_lookup(executions, exception_kwargs or {}))]
    messages = [Message(role="user", content="go")]
    if entry_point == "aresponse":
        await model.aresponse(messages=messages, tools=tools, tool_call_limit=TOOL_CALL_LIMIT)
    elif entry_point == "aresponse_stream":
        async for _ in model.aresponse_stream(messages=messages, tools=tools, tool_call_limit=TOOL_CALL_LIMIT):
            pass
    else:
        raise ValueError(entry_point)
    return len(executions)


ATTACHED_MESSAGE_CASES = {
    "no attached messages": {},
    "user_message": {"user_message": "Please retry with a different query."},
    "agent_message": {"agent_message": "That query failed, trying another approach."},
    "user_message and messages": {
        "user_message": "Please retry with a different query.",
        "messages": [
            Message(role="user", content="extra context"),
            {"role": "assistant", "content": "noted"},
        ],
    },
}


@pytest.mark.parametrize("entry_point", ["response", "response_stream"])
@pytest.mark.parametrize("case", ATTACHED_MESSAGE_CASES.values(), ids=ATTACHED_MESSAGE_CASES.keys())
def test_attached_messages_not_charged_sync(entry_point: str, case: Dict[str, Any]) -> None:
    assert run_sync(entry_point, case) == TOOL_CALL_LIMIT


@pytest.mark.parametrize("entry_point", ["aresponse", "aresponse_stream"])
@pytest.mark.parametrize("case", ATTACHED_MESSAGE_CASES.values(), ids=ATTACHED_MESSAGE_CASES.keys())
async def test_attached_messages_not_charged_async(entry_point: str, case: Dict[str, Any]) -> None:
    assert await run_async(entry_point, case) == TOOL_CALL_LIMIT


def test_limit_charge_counts_only_tool_results() -> None:
    model = LoopingModel()
    results = [
        Message(role="tool", content="ok", tool_name="lookup"),
        Message(role="user", content="Please retry with a different query."),
        Message(role="assistant", content="noted"),
    ]
    assert model._limit_charge_for(results, None) == 1


def test_limit_charge_keeps_offload_read_back_exemption() -> None:
    model = LoopingModel()
    results = [
        Message(role="tool", content="huge result", tool_name="lookup"),
        Message(role="tool", content="read-back", tool_name="read_result"),
        Message(role="user", content="Please retry with a different query."),
    ]
    # Any non-None result store enables the offload branch; read-back tools stay exempt.
    assert model._limit_charge_for(results, object()) == 1  # type: ignore[arg-type]
