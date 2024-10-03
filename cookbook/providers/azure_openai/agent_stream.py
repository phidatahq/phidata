"""Run `pip install yfinance` to install dependencies."""

import os
from typing import Iterator  # noqa

from dotenv import load_dotenv

from phi.agent import Agent, RunResponse  # noqa
from phi.model.azure import AzureOpenAIChat
from phi.tools.yfinance import YFinanceTools

load_dotenv()

azure_model = AzureOpenAIChat(
    id=os.getenv("AZURE_OPENAI_MODEL_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
)

agent = Agent(
    model=azure_model,
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
