"""
This recipe shows how an agent maintains long-term memory using a sqlite database.
Steps:
1. Run: `pip install openai sqlalchemy phidata` to install dependencies
2. Run: `python cookbook/memory/01_agent_with_long_term_memory.py` to run the agent
"""

import json

from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.storage.agent.sqlite import SqlAgentStorage


agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    # Store agent sessions in a database, that persists between runs
    storage=SqlAgentStorage(table_name="agent_sessions", db_file="tmp/agent_storage.db"),
    # add_history_to_messages=true adds the chat history to the messages sent to the Model.
    add_history_to_messages=True,
    # Number of historical responses to add to the messages.
    num_history_responses=3,
    # The session_id is used to identify the session in the database
    # You can resume any session by providing a session_id
    # session_id="xxxx-xxxx-xxxx-xxxx",
    # Description creates a system prompt for the agent
    description="You are a helpful assistant that always responds in a polite, upbeat and positive manner.",
)

console = Console()


def print_chat_history(agent):
    # -*- Print history
    console.print(
        Panel(
            JSON(json.dumps([m.model_dump(include={"role", "content"}) for m in agent.memory.messages]), indent=4),
            title=f"Chat History for session_id: {agent.session_id}",
            expand=True,
        )
    )


# -*- Create a run
agent.print_response("Share a 2 sentence horror story", stream=True)
# -*- Print the chat history
print_chat_history(agent)

# -*- Ask a follow up question that continues the conversation
agent.print_response("What was my first message?", stream=True)
# -*- Print the chat history
print_chat_history(agent)
