"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.xai import xAI
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=xAI(id="grok-beta"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("What is the stock price of TSLA")
