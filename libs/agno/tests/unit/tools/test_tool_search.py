"""Deferred tools behind tool search: which tools are deferred, and what the model is told.

A deferred tool is still sent to the provider, but its definition stays out of the model's
context until the model finds it with tool search. These tests pin the three decisions that
make that safe:

* Deferral is resolved per run, on the per-run copy of each Function, and only survives when
  tool search is on and the model supports it. Everywhere else the tool loads normally, so a
  fallback model or a provider without tool search never loses a tool.
* The flag never reaches a provider that does not support it.
* The searchable-tools index the system prompt carries is sorted and stable, so it does not
  break the prompt cache from one run to the next.
"""

from typing import List, Union

import pytest

from agno.agent import Agent
from agno.agent import _tools as agent_tools
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools import Toolkit, tool
from agno.tools import tool_search as tool_search_module
from agno.tools.function import Function
from agno.tools.tool_search import (
    DeferredTools,
    ToolSearch,
    summarize,
    tool_search_from_config,
    tool_search_to_config,
)
from agno.utils.tokens import count_tool_tokens


def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return "sunny"


def create_ticket(title: str) -> str:
    """Create an ITSM ticket."""
    return "SR-1"


def search_tickets(query: str) -> str:
    """Search ITSM tickets."""
    return "[]"


def close_ticket(ticket_id: str) -> str:
    """Close an ITSM ticket."""
    return "closed"


def _itsm(**kwargs) -> Toolkit:
    return Toolkit(name="serviceops", tools=[create_ticket, search_tickets, close_ticket], **kwargs)


def _parse(agent: Agent, tools: List) -> List[Union[Function, dict]]:
    return agent_tools.parse_tools(agent, tools=tools, model=agent.model)


def _flags(functions) -> dict:
    return {f.name: f.defer_loading for f in functions if isinstance(f, Function)}


@pytest.fixture(autouse=True)
def _reset_warned_models():
    tool_search_module._warned_models.clear()
    yield
    tool_search_module._warned_models.clear()


# --- Which tools a Toolkit defers ---


def test_toolkit_defer_loading_defers_every_tool():
    toolkit = _itsm(defer_loading=True)
    assert {name: f.defer_loading for name, f in toolkit.functions.items()} == {
        "create_ticket": True,
        "search_tickets": True,
        "close_ticket": True,
    }


def test_toolkit_deferred_tools_defers_only_those():
    toolkit = _itsm(deferred_tools=["close_ticket"])
    assert toolkit.functions["close_ticket"].defer_loading is True
    assert toolkit.functions["create_ticket"].defer_loading is None


def test_always_loaded_tools_override_toolkit_defer_loading():
    toolkit = _itsm(defer_loading=True, always_loaded_tools=["search_tickets"])
    assert toolkit.functions["search_tickets"].defer_loading is None
    assert toolkit.functions["create_ticket"].defer_loading is True


def test_decorator_value_wins_over_toolkit_setting():
    class ItsmTools(Toolkit):
        def __init__(self, **kwargs):
            super().__init__(name="itsm", tools=[self.lookup, self.purge], **kwargs)

        @tool(defer_loading=False)
        def lookup(self, query: str) -> str:
            """Look up a ticket."""
            return query

        @tool(defer_loading=True)
        def purge(self) -> str:
            """Purge closed tickets."""
            return "ok"

    toolkit = ItsmTools(defer_loading=True)
    assert toolkit.functions["lookup"].defer_loading is False
    assert toolkit.functions["purge"].defer_loading is True


def test_unknown_deferred_tool_names_warn_not_raise(caplog):
    _itsm(deferred_tools=["does_not_exist"])
    assert "Deferred tool(s) not present in the toolkit: does_not_exist" in caplog.text


# --- Per-run resolution on the agent ---


def test_supported_model_keeps_deferral_and_builds_index():
    agent = Agent(model=Claude(id="claude-opus-5-5"), tools=[get_weather, _itsm(defer_loading=True)])
    functions = _parse(agent, agent.tools)

    assert _flags(functions) == {
        "get_weather": None,
        "create_ticket": True,
        "search_tickets": True,
        "close_ticket": True,
    }
    assert agent._tool_search_index is not None
    assert "- serviceops (3 tools): close_ticket, create_ticket, search_tickets" in agent._tool_search_index


@pytest.mark.parametrize("model", [Claude(id="claude-sonnet-4-20250514"), OpenAIChat(id="gpt-4o")])
def test_model_without_tool_search_loads_deferred_tools_normally(model, caplog):
    agent = Agent(model=model, tools=[_itsm(defer_loading=True)])
    functions = _parse(agent, agent.tools)

    assert set(_flags(functions).values()) == {None}
    assert agent._tool_search_index is None
    assert "does not support tool search" in caplog.text


def test_unsupported_model_warning_is_logged_once_per_model(caplog):
    agent = Agent(model=OpenAIChat(id="gpt-4o"), tools=[_itsm(defer_loading=True)])
    _parse(agent, agent.tools)
    _parse(agent, agent.tools)
    assert caplog.text.count("does not support tool search") == 1


def test_tool_search_false_loads_deferred_tools_normally():
    agent = Agent(model=Claude(id="claude-opus-5-5"), tools=[_itsm(defer_loading=True)], tool_search=False)
    functions = _parse(agent, agent.tools)

    assert set(_flags(functions).values()) == {None}
    assert agent._tool_search_index is None


def test_clearing_the_flag_for_one_run_leaves_the_toolkit_untouched():
    toolkit = _itsm(defer_loading=True)
    _parse(Agent(model=OpenAIChat(id="gpt-4o"), tools=[toolkit]), [toolkit])

    # The per-run copies were cleared; the next run on a model with tool search still defers.
    assert toolkit.functions["create_ticket"].defer_loading is True
    agent = Agent(model=Claude(id="claude-opus-5-5"), tools=[toolkit])
    assert _flags(_parse(agent, [toolkit]))["create_ticket"] is True


def test_standalone_deferred_function_is_indexed_under_tools():
    @tool(defer_loading=True)
    def export_report(month: str) -> str:
        """Export the monthly report."""
        return month

    agent = Agent(model=Claude(id="claude-opus-5-5"), tools=[get_weather, export_report])
    functions = _parse(agent, agent.tools)

    assert _flags(functions)["export_report"] is True
    assert "- tools (1 tool): export_report" in agent._tool_search_index


def test_no_deferred_tools_means_no_index():
    agent = Agent(model=Claude(id="claude-opus-5-5"), tools=[get_weather, _itsm()])
    _parse(agent, agent.tools)
    assert agent._tool_search_index is None


# --- The searchable-tools index ---


def test_toolkits_index_lists_the_summary_only():
    toolkit = _itsm(defer_loading=True, tool_search_description="ITSM tickets: incidents, requests, changes.")
    agent = Agent(model=Claude(id="claude-opus-5-5"), tools=[toolkit], tool_search=ToolSearch(index="toolkits"))
    _parse(agent, agent.tools)
    assert "- serviceops (3 tools): ITSM tickets: incidents, requests, changes." in agent._tool_search_index
    assert "create_ticket" not in agent._tool_search_index


def test_default_index_lists_tool_names_after_the_summary():
    # A summary written for people may not say what the tools do; the names always do
    toolkit = _itsm(defer_loading=True, tool_search_description="ITSM tickets.")
    agent = Agent(model=Claude(id="claude-opus-5-5"), tools=[toolkit])
    _parse(agent, agent.tools)
    assert (
        "- serviceops (3 tools): ITSM tickets. Tools: close_ticket, create_ticket, search_tickets"
        in agent._tool_search_index
    )


def test_none_index_omits_the_block_but_keeps_deferral():
    agent = Agent(
        model=Claude(id="claude-opus-5-5"), tools=[_itsm(defer_loading=True)], tool_search=ToolSearch(index="none")
    )
    functions = _parse(agent, agent.tools)
    assert agent._tool_search_index is None
    assert set(_flags(functions).values()) == {True}


def test_index_is_identical_whatever_order_the_tools_arrive_in():
    first = Toolkit(name="b_tools", tools=[create_ticket], defer_loading=True)
    second = Toolkit(name="a_tools", tools=[search_tickets, close_ticket], defer_loading=True)

    one = Agent(model=Claude(id="claude-opus-5-5"), tools=[first, second])
    _parse(one, one.tools)
    two = Agent(model=Claude(id="claude-opus-5-5"), tools=[second, first])
    _parse(two, two.tools)

    assert one._tool_search_index == two._tool_search_index
    assert one._tool_search_index.index("- a_tools") < one._tool_search_index.index("- b_tools")


def test_summarize_keeps_the_first_paragraph_on_one_line_and_caps_it():
    assert summarize("Motadata ServiceOps (ITSM).\nTickets and assets.\n\nStart with whoami.") == (
        "Motadata ServiceOps (ITSM). Tickets and assets."
    )
    long = summarize("x" * 1000)
    assert long is not None and len(long) == 300 and long.endswith("...")
    assert summarize("   ") is None
    assert summarize(None) is None


def test_index_sits_with_the_tool_instructions_before_per_run_context():
    toolkit = _itsm(defer_loading=True)
    agent = Agent(
        model=Claude(id="claude-opus-5-5"),
        tools=[toolkit],
        expected_output="A ticket id.",
        additional_context="ADDITIONAL",
    )
    from agno.agent import _messages
    from agno.run import RunContext
    from agno.session import AgentSession

    functions = _parse(agent, agent.tools)
    message = _messages.get_system_message(
        agent,
        session=AgentSession(session_id="s"),
        run_context=RunContext(run_id="r", session_id="s"),
        tools=functions,
    )
    content = message.content
    assert content.index("<searchable_tools>") < content.index("<expected_output>") < content.index("ADDITIONAL")


# --- What reaches the provider ---


def test_format_tools_sets_defer_loading_only_for_models_with_tool_search():
    deferred = Function(name="create_ticket", description="Create", defer_loading=True)
    loaded = Function(name="get_weather", description="Weather")

    claude_tools = Claude(id="claude-opus-5-5")._format_tools([deferred, loaded])
    assert [t.get("defer_loading") for t in claude_tools] == [True, None]
    assert "defer_loading" not in claude_tools[0]["function"]

    openai_tools = OpenAIChat(id="gpt-4o")._format_tools([deferred, loaded])
    assert all("defer_loading" not in t and "defer_loading" not in t["function"] for t in openai_tools)


def test_defer_loading_is_not_part_of_the_saved_function():
    assert "defer_loading" not in Function(name="f", defer_loading=True).to_dict()


def test_local_token_count_skips_deferred_definitions():
    loaded = Function.from_callable(get_weather)
    deferred = Function.from_callable(create_ticket)
    deferred.defer_loading = True
    assert count_tool_tokens([loaded, deferred]) == count_tool_tokens([loaded])


# --- Stored component config ---


@pytest.mark.parametrize(
    "value, stored",
    [(True, True), (False, False), (ToolSearch(index="names"), {"index": "names"})],
)
def test_tool_search_config_round_trip(value, stored):
    assert tool_search_to_config(value) == stored
    restored = tool_search_from_config(stored)
    assert restored == value


def test_agent_config_keeps_tool_search():
    agent = Agent(model=Claude(id="claude-opus-5-5"), tool_search=ToolSearch(index="none"))
    config = agent.to_dict()
    assert config["tool_search"] == {"index": "none"}
    assert Agent.from_dict(config).tool_search == ToolSearch(index="none")


def test_deferred_tools_collector_without_tool_search_config_is_silent(caplog):
    collector = DeferredTools(OpenAIChat(id="gpt-4o"), False)
    function = Function(name="f", defer_loading=True)
    collector.add(function)
    assert function.defer_loading is None
    assert "does not support tool search" not in caplog.text
