from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.storage.agent.postgres import PgAgentStorage

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
    system_prompt="Your name is optimus",
    add_history_to_messages=True,
    markdown=True,
    # debug_mode=True,
)
agent.print_response("Share a 1 sentence horror story", stream=True)
agent.print_response("Share a 2 sentence horror story", stream=True)
agent.print_response("Share a 3 sentence horror story", stream=True)
agent.print_response("Share a 4 sentence horror story", stream=True)
agent.print_response("Share a 5 sentence horror story", stream=True)
