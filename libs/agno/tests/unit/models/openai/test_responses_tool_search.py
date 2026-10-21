"""OpenAI Responses requests with deferred tools.

GPT-5.4 and later search deferred tools with the hosted ``tool_search`` tool: each deferred
function carries ``defer_loading: true`` and ``{"type": "tool_search"}`` joins the tools. Every
other model, and every provider that only implements the Open Responses spec, loads deferred tools
normally, so a request never carries a tool type the endpoint does not know.
"""

import pytest

from agno.agent import Agent
from agno.agent import _tools as agent_tools
from agno.models.azure.openai_responses import AzureOpenAIResponses
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.openai.open_responses import OpenResponses
from agno.models.openai.responses import supports_tool_search
from agno.tools import Toolkit
from agno.tools.function import Function


def _deferred(name: str = "serviceops_tickets") -> Function:
    return Function(name=name, description=f"{name} tool", defer_loading=True)


def _loaded(name: str = "serviceops_whoami") -> Function:
    return Function(name=name, description=f"{name} tool")


@pytest.mark.parametrize(
    "model_id", ["gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5", "gpt-5.10", "gpt-6", "gpt-6-astra"]
)
def test_models_with_tool_search(model_id):
    assert supports_tool_search(model_id)


@pytest.mark.parametrize(
    "model_id", ["gpt-5.3", "gpt-5.2-codex", "gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o", "o3", "o4-mini"]
)
def test_models_without_tool_search(model_id):
    assert not supports_tool_search(model_id)


def test_deferred_tools_get_defer_loading_and_the_tool_search_tool():
    model = OpenAIResponses(id="gpt-5.4-mini")
    tools = model._format_tool_params([], model._format_tools([_loaded(), _deferred()]))

    by_name = {t.get("name"): t for t in tools}
    assert by_name["serviceops_tickets"]["defer_loading"] is True
    assert "defer_loading" not in by_name["serviceops_whoami"]
    assert tools[-1] == {"type": "tool_search"}


def test_function_objects_are_formatted_the_same_way():
    # count_tokens passes Function objects straight to _format_tool_params
    model = OpenAIResponses(id="gpt-5.4-mini")
    tools = model._format_tool_params([], [_loaded(), _deferred()])
    assert [t.get("defer_loading") for t in tools] == [None, True, None]
    assert tools[-1] == {"type": "tool_search"}


def test_a_tool_search_tool_the_caller_passed_is_not_duplicated():
    model = OpenAIResponses(id="gpt-5.4-mini")
    tools = model._format_tool_params([], model._format_tools([_deferred()]) + [{"type": "tool_search"}])
    assert [t for t in tools if t.get("type") == "tool_search"] == [{"type": "tool_search"}]


def test_no_deferred_tools_means_no_tool_search_tool():
    model = OpenAIResponses(id="gpt-5.4-mini")
    tools = model._format_tool_params([], model._format_tools([_loaded()]))
    assert all(t.get("type") != "tool_search" for t in tools)


@pytest.mark.parametrize(
    "model",
    [
        OpenAIResponses(id="gpt-5"),
        OpenResponses(id="openai/gpt-5.4"),
        AzureOpenAIResponses(id="gpt-5.4-mini", api_key="k", azure_endpoint="https://example.invalid"),
    ],
    ids=["gpt-5", "open-responses", "azure"],
)
def test_models_without_tool_search_load_deferred_tools_normally(model):
    tools = model._format_tool_params([], model._format_tools([_loaded(), _deferred()]))
    assert all("defer_loading" not in t for t in tools)
    assert all(t.get("type") != "tool_search" for t in tools)


def test_chat_completions_has_no_tool_search():
    assert not OpenAIChat(id="gpt-5.4").supports_tool_search()


def test_agent_on_gpt_5_4_defers_and_indexes():
    def search_tickets(query: str) -> str:
        """Search ITSM tickets."""
        return "[]"

    toolkit = Toolkit(name="serviceops", tools=[search_tickets], defer_loading=True, tool_search_description="ITSM.")
    agent = Agent(model=OpenAIResponses(id="gpt-5.4-mini"), tools=[toolkit])
    functions = agent_tools.parse_tools(agent, tools=[toolkit], model=agent.model)

    assert [f.defer_loading for f in functions] == [True]
    assert agent._tool_search_index is not None
    assert "- serviceops (1 tool): ITSM." in agent._tool_search_index


# --- Namespaces: a toolkit's deferred tools travel as one namespace ---


def _tickets(query: str) -> str:
    """Search ITSM tickets."""
    return "[]"


def _assign(ticket: str, assignee: str) -> str:
    """Assign an ITSM ticket."""
    return "ok"


def _whoami() -> str:
    """Who is the current user."""
    return "me"


def _formatted_for(*tools):
    model = OpenAIResponses(id="gpt-5.4-mini")
    agent = Agent(model=model, tools=list(tools))
    functions = agent_tools.parse_tools(agent, tools=list(tools), model=model)
    return model._format_tool_params([], model._format_tools(functions)), model, functions


def test_a_toolkits_deferred_tools_share_one_namespace():
    helpdesk = Toolkit(
        name="helpdesk",
        tools=[_tickets, _assign, _whoami],
        defer_loading=True,
        always_loaded_tools=["_whoami"],
        tool_search_description="ITSM tickets",
    )
    tools, _, _ = _formatted_for(helpdesk)

    namespaces = [t for t in tools if t.get("type") == "namespace"]
    assert len(namespaces) == 1
    namespace = namespaces[0]
    assert namespace["name"] == "helpdesk"
    assert namespace["description"] == "ITSM tickets. Tools: _assign, _tickets"
    assert [t["name"] for t in namespace["tools"]] == ["_assign", "_tickets"]
    assert all(t["defer_loading"] is True for t in namespace["tools"])
    # The always-loaded tool stays a top-level function, and the search tool closes the list
    assert any(t.get("name") == "_whoami" and "defer_loading" not in t for t in tools)
    assert tools[-1] == {"type": "tool_search"}


def test_function_objects_are_grouped_the_same_way():
    helpdesk = Toolkit(name="helpdesk", tools=[_tickets, _assign], defer_loading=True)
    via_dicts, model, functions = _formatted_for(helpdesk)
    assert model._format_tool_params([], functions) == via_dicts


def test_toolkits_sharing_a_name_get_separate_valid_namespaces():
    first = Toolkit(name="help desk!", tools=[_tickets], defer_loading=True)
    second = Toolkit(name="help desk!", tools=[_assign], defer_loading=True)
    tools, _, _ = _formatted_for(first, second)

    names = [t["name"] for t in tools if t.get("type") == "namespace"]
    assert names == ["help_desk_", "help_desk__2"]


def test_a_standalone_deferred_function_stays_flat():
    from agno.tools import tool

    @tool(defer_loading=True)
    def export_report(month: str) -> str:
        """Export the monthly report."""
        return month

    tools, _, _ = _formatted_for(export_report)
    assert [t.get("type") for t in tools] == ["function", "tool_search"]
    assert tools[0]["defer_loading"] is True
