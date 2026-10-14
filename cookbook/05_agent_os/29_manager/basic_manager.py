"""Serve an AgentOS with an OS manager.

Open the AgentOS UI, select OS Manager and ask it to run diagnostics.
This example needs only a model and a database. See manager_builds_agents.py
for an example that lets the manager create and run new agents.

Run:
    .venvs/demo/bin/python cookbook/05_agent_os/29_manager/basic_manager.py
"""

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, ManagerConfig

agent_os = AgentOS(
    name="Manager demo",
    db=SqliteDb(db_file="tmp/manager.db"),
    manager=ManagerConfig(model=OpenAIResponses(id="gpt-5.6-luna")),
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="basic_manager:app", reload=True)
