"""Run `pip install yfinance openai agno` to install dependencies."""

from agno.agent import Agent
from agno.models.openai import OpenAI
from agno.tools.yfinance import YFinanceTools

finance_agent = Agent(
    name="Finance Agent",
    model=OpenAI(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
)
finance_agent.print_response("Summarize and compare analyst recommendations for NVDA for TSLA", stream=True)
