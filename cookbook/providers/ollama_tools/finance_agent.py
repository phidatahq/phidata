"""Run `pip install yfinance ollama phidata` to install dependencies."""

from phi.agent import Agent
from phi.model.ollama import OllamaTools
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=OllamaTools(id="llama3.1:8b"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    instructions=["Use tables to display data"],
    markdown=True,
)

agent.print_response("Share fundamentals and analyst recommendations for TSLA in a table", stream=True)
