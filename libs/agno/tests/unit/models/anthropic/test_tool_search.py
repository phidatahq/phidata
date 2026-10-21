"""Claude requests with deferred tools must be ones the Anthropic API accepts.

Tool search has request-level rules that turn a small mistake into a 400:

* every tool cannot be deferred, so the tool search tool goes in whenever a tool is deferred;
* ``cache_control`` cannot sit on a deferred tool;
* a ``tool_reference`` in the history must name a tool the request defines, even when that
  tool has since gone away (an MCP server dropped it, or the tool set changed between runs);
* models before Opus 4.5 / Sonnet 4.5 / Haiku 4.5 do not support tool search at all, so they
  get every tool loaded instead.

Token counting is also covered: deferred definitions are not in the context window, so they
are not counted.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from agno.models.anthropic.claude import Claude
from agno.models.message import Message
from agno.tools.function import Function
from agno.utils.models.claude import add_tool_search, format_tools_for_model, supports_tool_search


def _formatted(model: Claude, *functions: Function) -> List[Dict[str, Any]]:
    return model._format_tools(list(functions))


def _deferred(name: str = "create_ticket") -> Function:
    return Function(name=name, description=f"{name} tool", defer_loading=True)


def _loaded(name: str = "get_weather") -> Function:
    return Function(name=name, description=f"{name} tool")


def _search_result_message(*tool_names: str) -> Message:
    """An assistant turn whose stored content holds a tool search and its result."""
    blocks = [
        {"type": "server_tool_use", "id": "srvtoolu_1", "name": "tool_search_tool_bm25", "input": {"query": "x"}},
        {
            "type": "tool_search_tool_result",
            "tool_use_id": "srvtoolu_1",
            "content": {
                "type": "tool_search_tool_search_result",
                "tool_references": [{"type": "tool_reference", "tool_name": n} for n in tool_names],
            },
        },
    ]
    return Message(role="assistant", content="", provider_data={"content_blocks": blocks})


@pytest.mark.parametrize(
    "model_id",
    [
        "claude-opus-5-5",
        "claude-fable-5-1",
        "claude-sonnet-5-5",
        "claude-haiku-5-5",
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-5-20251101",
        "claude-haiku-4-5",
        "claude-opus-4-8",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "anthropic.claude-opus-5-5",
        "claude-opus-4-5@20251101",
        "anthropic/claude-sonnet-4-6",
    ],
)
def test_models_with_tool_search(model_id):
    assert supports_tool_search(model_id)


@pytest.mark.parametrize(
    "model_id",
    [
        "claude-3-5-sonnet-20241022",
        "claude-3-7-sonnet-latest",
        "claude-3-5-haiku-20241022",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-opus-4-1-20250805",
        "claude-opus-4",
        "claude-sonnet-4",
        "claude-sonnet-4-0",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "claude-sonnet-4@20250514",
        "gpt-4o",
    ],
)
def test_models_without_tool_search(model_id):
    assert not supports_tool_search(model_id)


def test_format_tools_for_model_keeps_defer_loading():
    model = Claude(id="claude-opus-5-5")
    tools = format_tools_for_model(_formatted(model, _deferred(), _loaded()))
    assert tools is not None
    by_name = {t["name"]: t for t in tools}
    assert by_name["create_ticket"]["defer_loading"] is True
    assert "defer_loading" not in by_name["get_weather"]


def test_request_adds_the_tool_search_tool_when_a_tool_is_deferred():
    model = Claude(id="claude-opus-5-5")
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _deferred(), _loaded()))
    assert kwargs["tools"][-1] == {"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"}


def test_request_uses_the_regex_variant_when_configured():
    model = Claude(id="claude-opus-5-5", tool_search_variant="regex")
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _deferred()))
    assert kwargs["tools"][-1] == {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"}


def test_request_keeps_a_tool_search_tool_the_caller_passed():
    model = Claude(id="claude-opus-5-5")
    own = {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"}
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _deferred()) + [own])
    search_tools = [t for t in kwargs["tools"] if str(t.get("type", "")).startswith("tool_search_tool_")]
    assert search_tools == [own]


def test_request_without_deferred_tools_is_unchanged():
    model = Claude(id="claude-opus-5-5")
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _loaded()))
    assert [t["name"] for t in kwargs["tools"]] == ["get_weather"]


def test_request_without_tools_sends_no_tools():
    model = Claude(id="claude-opus-5-5")
    kwargs = model._prepare_request_kwargs("system", tools=None, messages=[Message(role="user", content="hi")])
    assert "tools" not in kwargs


def test_cache_control_goes_on_the_last_loaded_tool():
    model = Claude(id="claude-opus-5-5", cache_tools=True)
    # Name-sorted, the deferred tool would be last without the tool search tool after it.
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _loaded("a_tool"), _deferred("z_tool")))
    tagged = [t["name"] for t in kwargs["tools"] if "cache_control" in t]
    assert tagged == ["tool_search_tool_bm25"]
    assert all("cache_control" not in t for t in kwargs["tools"] if t.get("defer_loading"))


def test_cache_control_skips_deferred_tools_when_the_search_tool_comes_first():
    tools = [
        {"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"},
        {"name": "a_tool", "description": "", "input_schema": {"type": "object", "properties": {}}},
        {"name": "z_tool", "description": "", "input_schema": {"type": "object"}, "defer_loading": True},
    ]
    kwargs: Dict[str, Any] = {"tools": tools}
    Claude(id="claude-opus-5-5", cache_tools=True)._apply_cache_tools(kwargs)
    assert [t["name"] for t in kwargs["tools"] if "cache_control" in t] == ["a_tool"]


def test_tool_found_earlier_but_gone_now_gets_a_deferred_stub():
    model = Claude(id="claude-opus-5-5")
    history = [Message(role="user", content="open a ticket"), _search_result_message("create_ticket", "old_tool")]
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _deferred()), messages=history)

    by_name = {t["name"]: t for t in kwargs["tools"]}
    assert by_name["old_tool"]["defer_loading"] is True
    assert by_name["old_tool"]["description"] == "This tool is no longer available."
    # A tool that is still offered is not duplicated.
    assert [t["name"] for t in kwargs["tools"]].count("create_ticket") == 1


def test_history_with_tool_references_keeps_the_search_tool_without_deferred_tools():
    model = Claude(id="claude-opus-5-5")
    history = [Message(role="user", content="hi"), _search_result_message("old_tool")]
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _loaded()), messages=history)
    names = [t["name"] for t in kwargs["tools"]]
    assert "old_tool" in names and "tool_search_tool_bm25" in names


def test_model_without_tool_search_never_gets_the_search_tool():
    model = Claude(id="claude-sonnet-4-20250514")
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _deferred(), _loaded()))
    assert all(not str(t.get("type", "")).startswith("tool_search_tool_") for t in kwargs["tools"])
    assert all("defer_loading" not in t for t in kwargs["tools"])


@pytest.mark.parametrize(
    "module",
    [
        "agno.models.anthropic.claude",
        "agno.models.aws.claude",
        "agno.models.vertexai.claude",
        "agno.models.azure.claude",
    ],
)
def test_every_claude_provider_adds_the_tool_search_tool(module):
    # Bedrock, Vertex AI and Foundry build their own request kwargs; all of them support tool search.
    # Imported here, not at module level: see test_request_kwargs_match_sdk.py for why.
    from importlib import import_module

    model = import_module(module).Claude(id="claude-opus-5-5", cache_tools=True)
    kwargs = model._prepare_request_kwargs("system", tools=_formatted(model, _deferred(), _loaded()))

    assert kwargs["tools"][-1]["name"] == "tool_search_tool_bm25"
    assert all("cache_control" not in t for t in kwargs["tools"] if t.get("defer_loading"))


def test_add_tool_search_reads_server_tool_blocks_too():
    message = _search_result_message("old_tool")
    message.provider_data = {"server_tool_blocks": message.provider_data["content_blocks"]}
    tools = add_tool_search([], messages=[message])
    assert {t["name"] for t in tools} == {"old_tool", "tool_search_tool_bm25"}


def test_count_tokens_leaves_out_deferred_tools(monkeypatch):
    model = Claude(id="claude-opus-5-5")
    client = MagicMock()
    client.messages.count_tokens.return_value = MagicMock(input_tokens=42)
    monkeypatch.setattr(model, "get_client", lambda: client)

    model.count_tokens([Message(role="user", content="hi")], tools=[_deferred(), _loaded()])

    sent = client.messages.count_tokens.call_args.kwargs["tools"]
    assert [t["name"] for t in sent] == ["get_weather"]
