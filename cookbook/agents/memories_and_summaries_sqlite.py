"""
This recipe shows how to use personalized memories and summaries in an agent.
Steps:
1. Run: `./cookbook/run_pgvector.sh` to start a postgres and pgvector instance
2. Run: `pip install openai sqlalchemy` to install dependencies
3. Run: `python cookbook/agents/memories_and_summaries_sqlite.py` to run the agent
"""

from rich.pretty import pprint

from phi.agent import Agent, AgentMemory
from phi.model.openai import OpenAIChat
from phi.memory.db.sqlite import SqliteMemoryDb
from phi.storage.agent.sqlite import SqlAgentStorage

agent_memory_file: str = "tmp/agent_memory.db"
agent_storage_file: str = "tmp/agent_storage.db"

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    # The memories are personalized for this user
    user_id="john_billings",
    # Store the memories and summary in a table: agent_memory
    memory=AgentMemory(
        db=SqliteMemoryDb(
            table_name="agent_memory",
            db_file=agent_memory_file,
        ),
        # Create and store personalized memories for this user
        create_user_memories=True,
        # Update memories for the user after each run
        update_user_memories_after_run=True,
        # Create and store session summaries
        create_session_summary=True,
        # Update session summaries after each run
        update_session_summary_after_run=True,
    ),
    # Store agent sessions in a database
    storage=SqlAgentStorage(table_name="agent_sessions", db_file=agent_storage_file),
    description="You are a helpful assistant that always responds in a polite, upbeat and positive manner.",
    # Show debug logs so you can see the memory being created
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
