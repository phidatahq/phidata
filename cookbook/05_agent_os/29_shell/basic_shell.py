"""Serve an AgentOS with its shell: one team you talk to, built by the framework.

The shell is the conversational entry point to the OS. Its lead delegates to
Platform Builder (composes agents, teams and workflows from the registry),
Platform Manager (reads the runtime and runs diagnostics) and, when a workspace
is configured, Platform Engineer (reads the source). All four are served as
ordinary components: open the AgentOS UI and chat with the Agno team.

Run:
    .venvs/demo/bin/python cookbook/05_agent_os/29_shell/basic_shell.py
"""

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, ShellConfig
from agno.registry import Registry
from agno.tools.calculator import CalculatorTools
from agno.workflow.functions import csv_to_markdown_table, extract_json, json_to_csv

db = SqliteDb(db_file="tmp/shell.db")

# The registry is the build palette: what Platform Builder may compose from.
# The shell's own toolkits never enter it.
registry = Registry(
    models=[OpenAIResponses(id="gpt-5.6-luna")],
    tools=[CalculatorTools()],
    functions=[extract_json, json_to_csv, csv_to_markdown_table],
)

agent_os = AgentOS(
    name="Shell demo",
    db=db,
    registry=registry,
    # shell=True would take the registry's first model. ShellConfig also sets the name.
    shell=ShellConfig(name="Agno", model=OpenAIResponses(id="gpt-5.6-luna")),
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="basic_shell:app", reload=True)
