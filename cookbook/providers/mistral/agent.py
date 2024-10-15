"""Run `pip install yfinance` to install dependencies."""

import os

from phi.agent import Agent, RunResponse  # noqa
from phi.model.mistral import MistralChat
from phi.tools.yfinance import YFinanceTools

mistral_api_key = os.getenv("MISTRAL_API_KEY")

agent = Agent(
    model=MistralChat(
        id="mistral-large-latest",
        api_key=mistral_api_key,
    ),
    tools=[
        YFinanceTools(
            company_info=True,
            stock_fundamentals=True,
        )
    ],
    show_tool_calls=True,
    debug_mode=True,
    markdown=True,
)

# Get the response in a variable
# run: RunResponse = agent.run("What is the stock price of NVDA and TSLA")
# print(run.content)

# Print the response on the terminal
agent.print_response("Give me in-depth analysis of NVDA and TSLA")
