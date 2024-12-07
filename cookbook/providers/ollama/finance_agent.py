"""Run `pip install yfinance` to install dependencies."""

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=Ollama(id="llama3.1:8b"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    instructions="Use tables to display data",
    markdown=True,
)

agent.print_response(
    "Summarize and compare analyst recommendations and fundamentals for TSLA and NVDA. Show in tables.", stream=True
)
