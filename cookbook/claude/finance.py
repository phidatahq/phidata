from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.anthropic import Claude

assistant = Assistant(
    llm=Claude(model="claude-3-opus-20240229"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
)
assistant.print_response("Share the NVDA stock price and some analyst recommendations", markdown=True)
assistant.print_response("Summarize fundamentals for TSLA", markdown=True)
