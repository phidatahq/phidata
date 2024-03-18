from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.anthropic import Claude

assistant = Assistant(
    llm=Claude(),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    debug_mode=True,
)
assistant.print_response("Share the NVDA stock price and some analyst recommendations", markdown=True, stream=False)
# assistant.print_response("Summarize fundamentals for TSLA", markdown=True, stream=False)