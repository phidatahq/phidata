import asyncio

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)


async def main():
    await agent.aprint_response("What is the stock price of NVDA and TSLA")
    await agent.aprint_response("What is the stock price of NVDA and TSLA", stream=True)


asyncio.run(main())

agent.print_response("What is the stock price of NVDA and TSLA?")
agent.print_response("What is the stock price of NVDA and TSLA?", stream=True)
