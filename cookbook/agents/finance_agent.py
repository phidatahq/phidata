"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Use tables where possible"],
    show_tool_calls=True,
    markdown=True,
    # debug_mode=True,
)

agent.print_response("What is the stock price of NVDA", stream=True)
agent.print_response("What is the stock price of TSLA", stream=True)
