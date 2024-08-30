from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.assistant.postgres import PgAssistantStorage

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    storage=PgAssistantStorage(table_name="assistant_threads", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)
# assistant.create_thread()
assistant.print_response("What is the stock price of NVDA")

# assistant.storage.upgrade_schema()
