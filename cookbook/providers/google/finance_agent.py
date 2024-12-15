"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools.yfinance import YFinanceTools

finance_agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    instructions=["Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
)
finance_agent.print_response("Summarize and compare analyst recommendations for NVDA for TSLA", stream=True)
