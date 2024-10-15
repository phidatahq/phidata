"""Run `pip install openai duckduckgo-search yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        DuckDuckGo(),
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True),
    ],
    instructions=["Use tables where possible"],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Write a thorough report on NVDA, get all financial information and latest news", stream=True)
