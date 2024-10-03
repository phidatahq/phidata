from phi.agent import Agent
from phi.model.together import Together
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=Together(id="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    instructions=["Use tables to display data where possible."],
    markdown=True,
)

# agent.print_response("Share the NVDA stock price and analyst recommendations", stream=True)
agent.print_response("Summarize fundamentals for TSLA", stream=True)
