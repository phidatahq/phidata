"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.ollama import Hermes
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=Hermes(id="hermes3:8b"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    instructions=["Use tables to display data"],
    markdown=True,
)

agent.print_response("Summarize analyst recommendations and fundamentals for TSLA", stream=True)
