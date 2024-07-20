from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.cohere import CohereChat

assistant = Assistant(
    llm=CohereChat(model="command-r-plus"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    instructions=["Use tables to display data where possible."],
    markdown=True,
    # debug_mode=True,
)
# assistant.print_response("Share the NVDA stock price and analyst recommendations")
assistant.print_response("Summarize fundamentals for TSLA")
