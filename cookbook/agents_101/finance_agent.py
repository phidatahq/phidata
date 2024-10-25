"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools

def create_finance_agent():
    return Agent(
        name="Finance Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            company_info=True,
            company_news=True
        )],
        instructions=["Use tables to display data"],
        show_tool_calls=True,
        markdown=True,
    )

if __name__ == "__main__":
    finance_agent = create_finance_agent()
    finance_agent.print_response("Share analyst recommendations for NVDA", stream=True)
