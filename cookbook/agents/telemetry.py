from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)

response: RunResponse = agent.run("What is the stock price of NVDA")

print(response.content)

# agent.create_session()
# agent.print_response("What is the stock price of NVDA")
