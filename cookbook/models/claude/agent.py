"""Run `pip install yfinance` to install dependencies."""

from agno.agent import Agent, RunResponse  # noqa
from agno.models.anthropic import Claude
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=Claude(id="claude-3-5-sonnet-20241022"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
)

# Get the response in a variable
# run: RunResponse = agent.run("What is the stock price of NVDA and TSLA")
# print(run.content)

# Print the response in the terminal
agent.print_response("What is the stock price of NVDA and TSLA")