from phi.agent import Agent
from phi.model.xai import xAI
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=xAI(id="grok-beta"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    instructions=["Use tables to display data."],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Share analyst recommendations for TSLA", stream=True)
agent.print_response("Summarize fundamentals for TSLA", stream=True)
