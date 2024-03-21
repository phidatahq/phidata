from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.cohere import Cohere

assistant = Assistant(
    llm=Cohere(model="command-r"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
)
assistant.print_response("Share the NVDA stock price and some analyst recommendations", markdown=True, stream=False)
assistant.print_response("Summarize fundamentals for TSLA", markdown=True)
