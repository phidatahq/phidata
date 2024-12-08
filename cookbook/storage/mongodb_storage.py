"""Run `pip install duckduckgo-search pymongo openai` to install dependencies."""

from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.agent.mongodb import MongoAgentStorage

# MongoDB connection settings
db_url = "mongodb://localhost:27017"

agent = Agent(
    storage=MongoAgentStorage(collection_name="agent_sessions", db_url=db_url, db_name="phi"),
    tools=[DuckDuckGo()],
    add_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
