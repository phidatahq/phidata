from phi.agent import Agent
from phi.tools.yfinance import YFinanceTools
from phi.model.anthropic import Claude

agent = Agent(
    model=Claude(model="claude-3-5-sonnet-20240620"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    instructions=["Use tables to display data where possible."],
    markdown=True,
    # debug_mode=True,
)
agent.print_response("Summarize fundamentals for TSLA")
# agent.print_response("Share the NVDA stock price and analyst recommendations")
