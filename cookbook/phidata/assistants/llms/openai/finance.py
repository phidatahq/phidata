from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.openai import OpenAIChat

assistant = Assistant(
    name="Finance Assistant",
    llm=OpenAIChat(model="gpt-4-turbo", max_tokens=500, temperature=0.3),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    show_tool_calls=True,
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    instructions=["Format your response using markdown and use tables to display data where possible."],
    # debug_mode=True,
)
assistant.print_response("Share the NVDA stock price and analyst recommendations", markdown=True)
# assistant.print_response("Summarize fundamentals for TSLA", markdown=True)
