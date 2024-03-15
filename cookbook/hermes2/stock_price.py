from phi.assistant import Assistant
from phi.tools.yfinance import YFinanceTools
from phi.llm.ollama import Hermes

assistant = Assistant(
    llm=Hermes(model="adrienbrault/nous-hermes2pro:Q8_0"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True)],
    show_tool_calls=True,
    # debug_mode=True,
)
assistant.print_response("Share the NVDA stock price and some analyst recommendations", markdown=True)
