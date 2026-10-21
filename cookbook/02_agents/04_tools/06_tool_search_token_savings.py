"""
Tool Search Token Savings
=========================
Counts the input tokens of one request with a large tool catalog, first with every tool
loaded and then with the catalog deferred behind tool search, index included. Counting
uses the provider's token counting endpoint, so no response is generated.

Pass `Claude(id="claude-opus-5-5")` instead to count with Anthropic. On Claude a deferred tool
leaves the context entirely; on OpenAI its name and description stay and only the parameter
schema is deferred, so the saving is smaller.
"""

from typing import Callable, List

from agno.models.base import Model
from agno.models.message import Message
from agno.models.openai import OpenAIResponses
from agno.tools import Toolkit
from agno.tools.tool_search import DeferredTools

# ---------------------------------------------------------------------------
# A Large Tool Catalog
# ---------------------------------------------------------------------------

SERVICES = ["github", "slack", "jira", "pagerduty", "grafana", "sentry"]
ACTIONS = [
    "list",
    "get",
    "create",
    "update",
    "delete",
    "search",
    "assign",
    "comment_on",
    "archive",
    "export",
]


def make_tool(service: str, action: str) -> Callable[..., str]:
    def tool_fn(
        resource_id: str,
        query: str = "",
        limit: int = 20,
        include_archived: bool = False,
    ) -> str:
        return f"{service}.{action}({resource_id})"

    tool_fn.__name__ = f"{service}_{action}"
    tool_fn.__doc__ = (
        f"{action.replace('_', ' ').capitalize()} {service} resources. Supports filtering by a free-text "
        f"query, a result limit, and whether archived {service} items are included."
    )
    return tool_fn


def catalog(defer: bool) -> List[Toolkit]:
    return [
        Toolkit(
            name=service,
            tools=[make_tool(service, action) for action in ACTIONS],
            defer_loading=defer,
            tool_search_description=f"{service.capitalize()}: {', '.join(ACTIONS)}.",
        )
        for service in SERVICES
    ]


# ---------------------------------------------------------------------------
# Count Tokens
# ---------------------------------------------------------------------------


def input_tokens(model: Model, defer: bool) -> int:
    # The searchable-tools index an Agent adds to its system prompt when tools are deferred
    index = DeferredTools(model, tool_search=True)
    functions = []
    for toolkit in catalog(defer):
        for function in toolkit.get_functions().values():
            # What an Agent does on every run: a per-run copy with its parameter schema built
            function = function.model_copy(deep=True)
            function.process_entrypoint()
            index.add(function, toolkit=toolkit)
            functions.append(function)
    system = index.get_system_prompt_snippet() or "You are a helpful assistant."

    messages = [
        Message(role="system", content=system),
        Message(role="user", content="Open a Jira ticket for the failing deploy."),
    ]
    return model.count_tokens(messages, tools=functions)


if __name__ == "__main__":
    model = OpenAIResponses(id="gpt-5.4-mini")
    loaded = input_tokens(model, defer=False)
    deferred = input_tokens(model, defer=True)
    print(f"{len(SERVICES) * len(ACTIONS)} tools in {len(SERVICES)} toolkits")
    print(f"All tools loaded:   {loaded:>6} input tokens")
    print(f"Deferred + index:   {deferred:>6} input tokens")
    print(
        f"Saved per request:  {loaded - deferred:>6} ({(loaded - deferred) / loaded:.0%})"
    )
