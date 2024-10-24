"""
This recipe shows how to use personalized memories and summaries in an agent.
Steps:
1. Run: `./cookbook/run_pgvector.sh` to start a postgres and pgvector instance
2. Run: `pip install anthropic sqlalchemy 'psycopg[binary]' pgvector` to install the dependencies
3. Run: `python cookbook/agents/personalized_memories_and_summaries.py` to run the agent
"""

from rich.pretty import pprint

from phi.agent import Agent, AgentMemory
from phi.model.azure import AzureOpenAIChat
from phi.memory.db.postgres import PgMemoryDb
from phi.storage.agent.postgres import PgAgentStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
agent = Agent(
    model=AzureOpenAIChat(id="gpt-4o"),
    # Store the memories and summary in a database
    memory=AgentMemory(db=PgMemoryDb(table_name="agent_memory", db_url=db_url)),
    add_history_to_messages=True,
    # Store agent sessions in a database
    storage=PgAgentStorage(table_name="personalized_agent_sessions", db_url=db_url),
    # Show debug logs so, you can see the memory being created
    # debug_mode=True,
)

# -*- Share personal information
agent.print_response("My name is john billings?", stream=True)
# -*- Print memories
pprint(agent.memory.memories)
# -*- Print summary
pprint(agent.memory.summary)

# -*- Share personal information
agent.print_response("I live in nyc?", stream=True)
# -*- Print memories
pprint(agent.memory.memories)
# -*- Print summary
pprint(agent.memory.summary)

# -*- Share personal information
agent.print_response("I'm going to a concert tomorrow?", stream=True)
# -*- Print memories
pprint(agent.memory.memories)
# -*- Print summary
pprint(agent.memory.summary)

# Ask about the conversation
agent.print_response("What have we been talking about, do you know my name?", stream=True)
