"""Run `pip install duckduckgo-search sqlalchemy groq` to install dependencies."""

from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.agent.postgres import PgAgentStorage

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

agent = Agent(
    model=Groq(id="llama3-groq-70b-8192-tool-use-preview"),
    storage=PgAgentStorage(table_name="agent_sessions", db_url=db_url),
    tools=[DuckDuckGo()],
    add_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
