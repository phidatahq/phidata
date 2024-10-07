"""Run `pip install duckduckgo-search sqlalchemy openai` to install dependencies."""

from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.agent.sqlite import SqlAgentStorage

agent = Agent(
    storage=SqlAgentStorage(table_name="agent_runs", db_file="tmp/data.db"),
    tools=[DuckDuckGo()],
    add_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
