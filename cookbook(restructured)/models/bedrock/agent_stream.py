"""Run `pip install yfinance` to install dependencies."""

from typing import Iterator  # noqa
from agno.agent import Agent, RunResponse  # noqa
from agno.models.aws.claude import Claude
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=Claude(id="anthropic.claude-3-5-sonnet-20240620-v1:0"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("What is the stock price of NVDA and TSLA", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response in the terminal
agent.print_response("What is the stock price of NVDA and TSLA", stream=True)
