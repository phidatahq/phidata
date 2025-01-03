"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent, RunResponse  # noqa
from phi.model.azure import AzureOpenAIChat
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=AzureOpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
)

# Get the response in a variable
# run: RunResponse = agent.run("What is the stock price of NVDA and TSLA")
# print(run.content)

# Print the response on the terminal
agent.print_response("What is the stock price of NVDA and TSLA")
