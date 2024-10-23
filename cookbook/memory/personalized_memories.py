from rich.pretty import pprint

from phi.agent import Agent, AgentMemory
from phi.model.openai import OpenAIChat
from phi.memory.db.postgres import PgMemoryDb
from phi.storage.agent.postgres import PgAgentStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    # Store the memories in a database
    memory=AgentMemory(db=PgMemoryDb(table_name="agent_memory", db_url=db_url), create_user_memories=True),
    # Store runs in a database
    storage=PgAgentStorage(table_name="personalized_agent_sessions", db_url=db_url),
    # Show debug logs so you can see the memory being created
    debug_mode=True,
)

# -*- Share personal information
agent.print_response("My name is john billings?", stream=True)
# -*- Print memories
pprint(agent.memory.memories)

# -*- Share personal information
agent.print_response("I live in nyc?", stream=True)
# -*- Print memories
pprint(agent.memory.memories)
