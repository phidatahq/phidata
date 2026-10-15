"""Ask Platform Manager about this source directory and Agno documentation.

Ask: "Read basic_manager.py and explain how this OS is configured."
Then: "Check the Agno docs and explain how to add a knowledge base."

Requires OPENAI_API_KEY for conversations and network access for docs MCP.
Source tools can read/search this directory, but cannot edit files or run code.
Set docs=False to use source tools without connecting to the documentation server.

Run:
    .venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_source.py
"""

from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, OSManager

agent_os = AgentOS(
    name="Manager source and docs",
    db=SqliteDb(db_file="tmp/manager_source.db"),
    manager=OSManager(
        model=OpenAIResponses(id="gpt-5.6-luna"),
        root=Path(__file__).parent,
        docs=True,
    ),
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="manager_source:app", reload=True)
