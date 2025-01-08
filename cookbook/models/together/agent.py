"""Run `pip install yfinance` to install dependencies."""

from agno.agent import Agent, RunResponse  # noqa
from agno.models.together import Together
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=Together(id="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
)

# Get the response in a variable
# run: RunResponse = agent.run("What is the stock price of NVDA and TSLA")
# print(run.content)

# Print the response on the terminal
agent.print_response("What is the stock price of NVDA and TSLA")
