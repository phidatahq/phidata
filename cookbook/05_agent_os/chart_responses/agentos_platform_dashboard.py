"""
AgentOS Platform Dashboard
==========================

Demonstrates an agent that charts real data instead of illustrative numbers.

A worker agent generates traced activity. A dashboard agent then combines two
toolkits: AgentOSTools reads the platform's own metrics, run activity, and tool
statistics from the database, and ChartTools turns each result into a validated
chart block. The agent chains the calls, fetching the data first and charting it
second, so every chart in Agno OS is grounded in a tool result.

Prerequisites: export OPENAI_API_KEY=...
Run: .venvs/demo/bin/python cookbook/05_agent_os/chart_responses/agentos_platform_dashboard.py
Try: ask the Platform Dashboard "Chart token usage by day and the model mix."
"""

from pathlib import Path

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS
from agno.os.config import AgentOSConfig, ChatConfig
from agno.tools.agentos import AgentOSTools
from agno.tools.calculator import CalculatorTools
from agno.tools.chart import ChartTools

DB_DIR = Path(__file__).parent / "tmp"
DB_DIR.mkdir(exist_ok=True)

db = SqliteDb(
    id="platform-dashboard-db", db_file=str(DB_DIR / "agentos_platform_dashboard.db")
)

# ---------------------------------------------------------------------------
# Worker: produces the traced activity the dashboard charts
# ---------------------------------------------------------------------------

worker = Agent(
    id="research-worker",
    name="Research Worker",
    model=OpenAIResponses(id="gpt-5.6-luna"),
    db=db,
    tools=[CalculatorTools()],
    instructions="Answer briefly. Use the calculator for any arithmetic.",
)

# ---------------------------------------------------------------------------
# Dashboard: reads platform data with AgentOSTools, charts it with ChartTools
# ---------------------------------------------------------------------------

dashboard_agent = Agent(
    id="platform-dashboard",
    name="Platform Dashboard",
    model=OpenAIResponses(id="gpt-5.6-luna"),
    db=db,
    tools=[AgentOSTools(db=db), ChartTools()],
    instructions=[
        "You build visual reports about this AgentOS deployment.",
        "Always fetch data with an AgentOSTools call before creating a chart. Never invent numbers.",
        "Pick the chart from the shape of the data:",
        "- daily token usage: bar-stacked with input and output tokens per date",
        "- runs or sessions over time: line chart keyed by date",
        "- model mix or share of runs: pie chart keyed by model",
        "- per-agent latency or tool duration: bar-horizontal sorted by value",
        "Use the date strings and metric names exactly as the tool returned them.",
        "If a window has no data, say so instead of charting an empty series.",
        "Mention the time window and any backend notes the tool included.",
    ],
    markdown=True,
)

agent_os = AgentOS(
    id="platform-dashboard-demo",
    description="AgentOS cookbook for charting live platform metrics in Agno OS.",
    agents=[worker, dashboard_agent],
    db=db,
    tracing=True,
    config=AgentOSConfig(
        chat=ChatConfig(
            quick_prompts={
                "platform-dashboard": [
                    "Chart token usage by day and the model mix.",
                    "Show runs per agent for the last 7 days with average latency.",
                    "Which tools were used most and how long did they take?",
                ],
            },
        ),
    ),
)
app = agent_os.get_app()


def seed_activity() -> None:
    """Run the worker a few times so the dashboard has traces and metrics to chart."""
    prompts = ["What is 41 * 73?", "What is 12 + 30?", "What is 2 ** 10?"]
    for prompt in prompts:
        worker.run(prompt, session_id="dashboard-seed-session", user_id="demo-user")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    seed_activity()
    agent_os.serve(app="agentos_platform_dashboard:app", port=7777)
