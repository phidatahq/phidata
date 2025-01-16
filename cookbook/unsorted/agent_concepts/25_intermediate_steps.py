from typing import Iterator
from rich.pretty import pprint
from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAI
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=OpenAI(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    markdown=True,
    show_tool_calls=True,
)

run_stream: Iterator[RunResponse] = agent.run(
    "What is the stock price of NVDA", stream=True, stream_intermediate_steps=True
)
for chunk in run_stream:
    pprint(chunk.model_dump(exclude={"messages"}))
    print("---" * 20)
