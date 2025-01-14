"""Run `pip install yfinance` to install dependencies."""

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.yfinance import YFinanceTools

finance_agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    instructions=["Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
)
finance_agent.print_response("Summarize and compare analyst recommendations for NVDA for TSLA", stream=True)
