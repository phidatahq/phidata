"""
This recipe shows how to use personalized memories and summaries in an agent.
Steps:
1. Run: `./cookbook/run_pgvector.sh` to start a postgres and pgvector instance
2. Run: `pip install openai sqlalchemy 'psycopg[binary]' pgvector` to install the dependencies
3. Run: `python cookbook/agents/personalized_memories_and_summaries.py` to run the agent
"""

from rich.pretty import pprint

from phi.agent import Agent, AgentMemory
from phi.model.openai import OpenAIChat
from phi.memory.db.postgres import PgMemoryDb
from phi.storage.agent.postgres import PgAgentStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    user_id="ab",
    # Store the memories and summary in a database
    memory=AgentMemory(
        db=PgMemoryDb(table_name="agent_memory", db_url=db_url), create_user_memories=True, create_session_summary=True
    ),
    # Store agent sessions in a database
    storage=PgAgentStorage(table_name="personalized_agent_sessions", db_url=db_url),
)

message = ""
while message != "exit":
    message = input("Enter a message: ")
    agent.print_response(message, stream=True)
    pprint(agent.memory.memories)
    pprint(agent.memory.summary)
