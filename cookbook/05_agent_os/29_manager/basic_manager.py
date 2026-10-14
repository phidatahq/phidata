"""Serve an AgentOS with an OS manager.

Chat with OS Manager to build and run agents, teams and workflows.
Platform Builder creates them using the registry. Platform Manager checks
activity and runs diagnostics. Add a workspace to enable Platform Engineer
to read source code. Open the AgentOS UI and select OS Manager to try it.

Run:
    .venvs/demo/bin/python cookbook/05_agent_os/29_manager/basic_manager.py
"""

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS
from agno.registry import Registry
from agno.tools.calculator import CalculatorTools
from agno.workflow.functions import csv_to_markdown_table, extract_json, json_to_csv

db = SqliteDb(db_file="tmp/manager.db")

# The registry contains a set of components the Platform Builder may compose from.
registry = Registry(
    models=[OpenAIResponses(id="gpt-5.6-luna")],
    tools=[CalculatorTools()],
    functions=[extract_json, json_to_csv, csv_to_markdown_table],
)

agent_os = AgentOS(
    name="Manager demo",
    db=db,
    registry=registry,
    manager=True,
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="basic_manager:app", reload=True)
