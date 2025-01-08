"""Run `pip install yfinance` to install dependencies."""

from typing import Iterator  # noqa
from agno.agent import Agent, RunResponse  # noqa
from agno.models.azure import AzureOpenAIChat
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=AzureOpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("What is the stock price of NVDA and TSLA", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("What is the stock price of NVDA and TSLA", stream=True)
