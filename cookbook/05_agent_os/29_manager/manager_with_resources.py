"""Attach application resources to the manager: a notebook, knowledge, learning and the source.

Resources attached here ride the lead team. They do not enter the registry, so a
component built by Platform Builder cannot pick them up unless the application
also declares them on the registry.

Run:
    .venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_with_resources.py
"""

from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.fs import FileSystem
from agno.knowledge import Knowledge
from agno.learn import (
    LearningMachine,
    LearningMode,
    UserMemoryConfig,
    UserProfileConfig,
)
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, ManagerConfig
from agno.registry import Registry

db = SqliteDb(db_file="tmp/manager_resources.db")
model = OpenAIResponses(id="gpt-5.6-luna")

# A shared notebook for the platform. The manager gets the full toolkit; the registry
# gets an append-only view for built components.
notes = FileSystem(db, namespace="shared-notes", user_scoped=False)

# Per-user memory for the lead.
memory = LearningMachine(
    name="manager-memory",
    db=db,
    model=model,
    user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
    user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
)

product_knowledge = Knowledge(name="product-knowledge", contents_db=db)

registry = Registry(
    models=[model],
    tools=[
        notes.tools(
            name="shared_notes",
            include_tools=["read_file", "append_file", "list_files", "search_content"],
        )
    ],
    knowledge=[product_knowledge],
)

agent_os = AgentOS(
    name="Manager with resources",
    db=db,
    registry=registry,
    manager=ManagerConfig(
        name="Agno",
        model=model,
        tools=[notes.tools()],
        knowledge=product_knowledge,
        learning=memory,
        # The engineer reads this directory in tools mode; env and credential files are excluded.
        workspace=Path(__file__).parent,
        instructions=notes.instructions(),
    ),
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="manager_with_resources:app", reload=True)
