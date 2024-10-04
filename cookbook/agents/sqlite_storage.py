"""Run `pip install duckduckgo-search sqlalchemy openai` to install dependencies."""

from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.agent.sqllite import SqlAgentStorage

agent = Agent(
    storage=SqlAgentStorage(table_name="recipes", db_file="data.db"),
    tools=[DuckDuckGo()],
    add_chat_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
