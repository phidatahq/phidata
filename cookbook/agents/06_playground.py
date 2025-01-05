"""Run `pip install openai yfinance duckduckgo-search phidata 'fastapi[standard]' sqlalchemy` to install dependencies."""

from agno.agent import Agent
from agno.model.openai import OpenAIChat
from agno.storage.agent.sqlite import SqlAgentStorage
from agno.tools.duckduckgo import DuckDuckGo
from agno.tools.yfinance import YFinanceTools
from agno.playground import Playground, serve_playground_app

web_agent = Agent(
    name="Web Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    storage=SqlAgentStorage(table_name="web_agent", db_file="agents.db"),
    add_history_to_messages=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(enable_all=True)],
    instructions=["Use tables to display data"],
    # Add long-term memory to the agent
    storage=SqlAgentStorage(table_name="finance_agent", db_file="agents.db"),
    # Add history from long-term memory to the agent's messages
    add_history_to_messages=True,
    markdown=True,
)

app = Playground(agents=[finance_agent, web_agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("06_playground:app", reload=True)
