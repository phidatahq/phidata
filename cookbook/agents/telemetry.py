import asyncio  # noqa
from typing import Iterator  # noqa
from rich.pretty import pprint  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    # debug_mode=True,
    # monitoring=False,
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)

run1: RunResponse = agent.run("What is the stock price of NVDA")  # type: ignore
pprint(run1)
# print("------------*******************------------")
# print(run)
# print("------------*******************------------")
# print("------------*******************------------")
# for m in run.messages:
#     print("---")
#     print(m)
#     print("---")

# run: Iterator[RunResponse] = agent.run("What is the stock price of NVDA", stream=True)
# for chunk in run:
#     print(chunk.content)

# async def main():
#     async for chunk in await agent.arun("What is the stock price of NVDA", stream=True):
#         print(chunk.content)

# asyncio.run(main())
# agent.create_session()
# agent.print_response("What is the stock price of NVDA?")
