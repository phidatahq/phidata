"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools

finance_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    show_tool_calls=True,
    markdown=True,
)

finance_agent.print_response("Write a report comparing NVDA to TSLA", stream=True)
