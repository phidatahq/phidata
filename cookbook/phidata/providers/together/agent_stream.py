"""Run `pip install yfinance` to install dependencies."""

from typing import Iterator  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.together import Together
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=Together(id="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"),
    tools=[YFinanceTools(stock_price=True)],
    instructions=["Use tables where possible."],
    show_tool_calls=True,
    markdown=True,
)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("What is the stock price of NVDA and TSLA", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("What is the stock price of NVDA and TSLA", stream=True)
