"""Serve an AgentOS with its manager: one team you talk to, built by the framework.

The manager is the conversational entry point to the OS. Its lead delegates to
Platform Builder (composes agents, teams and workflows from the registry),
Platform Manager (reads the runtime and runs diagnostics) and, when a workspace
is configured, Platform Engineer (reads the source). All four are served as
ordinary components: open the AgentOS UI and chat with the Agno team.

Run:
    .venvs/demo/bin/python cookbook/05_agent_os/29_manager/basic_manager.py
"""

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, ManagerConfig
from agno.registry import Registry
from agno.tools.calculator import CalculatorTools
from agno.workflow.functions import csv_to_markdown_table, extract_json, json_to_csv

db = SqliteDb(db_file="tmp/manager.db")

# The registry is the build palette: what Platform Builder may compose from.
# The manager's own toolkits never enter it.
registry = Registry(
    models=[OpenAIResponses(id="gpt-5.6-luna")],
    tools=[CalculatorTools()],
    functions=[extract_json, json_to_csv, csv_to_markdown_table],
)

agent_os = AgentOS(
    name="Manager demo",
    db=db,
    registry=registry,
    # manager=True would take the registry's first model. ManagerConfig also sets the name.
    manager=ManagerConfig(name="Agno", model=OpenAIResponses(id="gpt-5.6-luna")),
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="basic_manager:app", reload=True)
