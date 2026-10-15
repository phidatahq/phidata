"""Give OS Manager chart tools while Platform Manager retrieves the data.

Requires ChartTools from PR #8295 (pending merge). Use a database with recorded
platform metrics; an empty database should produce a no-data answer.

Run after installing a version with ChartTools:
    .venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_charts.py

Ask: "Show daily agent runs for the last seven days as a line chart."
This serving example makes model calls when you send a message.
"""

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, OSManager
from agno.tools.chart import ChartTools

agent_os = AgentOS(
    name="Manager with charts",
    # Shares the basic manager example's data. Point this at your deployment's
    # database to chart its recorded metrics. Use PostgreSQL in production.
    db=SqliteDb(db_file="tmp/manager.db"),
    manager=OSManager(
        model=OpenAIResponses(id="gpt-5.6-luna"),
        tools=[ChartTools()],
        offload_tool_results=True,
    ),
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="manager_charts:app", reload=True)
