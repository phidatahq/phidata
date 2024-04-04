from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.groq import Groq

assistant = Assistant(
    llm=Groq(model="mixtral-8x7b-32768"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
)
assistant.print_response("Share the NVDA stock price and some analyst recommendations", markdown=True, stream=False)
assistant.print_response("Summarize fundamentals for TSLA", markdown=True, stream=False)
