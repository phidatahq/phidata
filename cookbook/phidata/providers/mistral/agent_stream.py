"""Run `pip install yfinance` to install dependencies."""

import os

from typing import Iterator  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.mistral import MistralChat
from phi.tools.yfinance import YFinanceTools

mistral_api_key = os.getenv("MISTRAL_API_KEY")

agent = Agent(
    model=MistralChat(
        id="mistral-large-latest",
        api_key=mistral_api_key,
    ),
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
