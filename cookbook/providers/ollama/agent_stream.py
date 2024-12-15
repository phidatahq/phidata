"""Run `pip install yfinance` to install dependencies."""

from typing import Iterator  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.ollama import Ollama
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=Ollama(id="llama3.1:8b"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True)],
    instructions="Use tables to display data.",
    show_tool_calls=True,
    markdown=True,
)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("What is the stock price of NVDA and TSLA", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response in the terminal
agent.print_response("What are analyst recommendations for NVDA and TSLA", stream=True)
