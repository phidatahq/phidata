"""
Deferred Tools With Tool Search
===============================
Mark tools `defer_loading` to keep their definitions out of the model's context. The
model sees a short index of what it can search for, finds the tools it needs with
the provider's tool search, and only then loads their full definitions.

- `Toolkit(defer_loading=True)` defers every tool in a toolkit.
- `deferred_tools=[...]` defers some, `always_loaded_tools=[...]` keeps some loaded.
- `@tool(defer_loading=True)` defers a single function.
- `Agent(tool_search=ToolSearch(index=...))` picks what the index lists; it is on by
  default whenever a tool is deferred, and `tool_search=False` turns it off.

Tool search runs on OpenAI GPT-5.4 and newer (`OpenAIResponses`) and on Claude Opus 4.5 /
Sonnet 4.5 / Haiku 4.5 and newer (`Claude(id="claude-opus-5-5")` works as a drop-in).
Other models load deferred tools normally.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.tools import Toolkit
from agno.tools.tool_search import ToolSearch

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def get_current_time(timezone: str) -> str:
    """Get the current time in a timezone, for example 'Europe/Berlin'."""
    return f"It is 10:42 in {timezone}."


def search_tickets(query: str, status: str = "open") -> str:
    """Search ITSM tickets (incidents, service requests, problems, changes) by text and status."""
    return f"SR-924 (P1, {status}): Payment gateway timeouts -- matches '{query}'"


def create_ticket(title: str, priority: str = "P3") -> str:
    """Create an ITSM ticket and return its number."""
    return f"Created SR-1001 '{title}' with priority {priority}"


def assign_ticket(ticket: str, assignee: str) -> str:
    """Assign an ITSM ticket to a person or group."""
    return f"{ticket} assigned to {assignee}"


def list_alerts(severity: str = "critical") -> str:
    """List firing monitoring alerts, optionally filtered by severity."""
    return f"2 {severity} alerts: db-01 CPU 97%, payments-api p99 latency 4.2s"


def get_metric(monitor: str, metric: str) -> str:
    """Get the latest value of a metric for a monitor, for example 'db-01', 'cpu.percent'."""
    return f"{monitor} {metric} = 97"


def run_ping(host: str) -> str:
    """Ping a host from the monitoring appliance."""
    return f"{host}: 4 packets, 0% loss, 12 ms"


helpdesk = Toolkit(
    name="helpdesk",
    tools=[search_tickets, create_ticket, assign_ticket],
    defer_loading=True,
    tool_search_description="ITSM tickets: search, create and assign incidents, requests, problems and changes.",
)

monitoring = Toolkit(
    name="monitoring",
    tools=[list_alerts, get_metric, run_ping],
    defer_loading=True,
    always_loaded_tools=["list_alerts"],
    tool_search_description="Monitoring: metrics for monitors and network checks from the appliance.",
)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------

agent = Agent(
    model=OpenAIResponses(id="gpt-5.4-mini"),
    tools=[get_current_time, helpdesk, monitoring],
    # The default index lists each toolkit's summary and tool names; "toolkits" lists summaries only
    tool_search=ToolSearch(index="names"),
    markdown=True,
)

# ---------------------------------------------------------------------------
# Run Agent
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # list_alerts is loaded; the ticket tools are found with tool search first
    run = agent.run(
        "Are there critical alerts right now? If the payments API is affected, find the open "
        "ticket for it and assign it to the payments-oncall group."
    )
    print(run.content)
    print("\nTools called:", [t.tool_name for t in run.tools or []])
    if run.metrics is not None:
        print("Input tokens:", run.metrics.input_tokens)
