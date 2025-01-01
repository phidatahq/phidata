from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.assistant.postgres import PgAssistantStorage

assistant = Assistant(
    storage=PgAssistantStorage(table_name="assistant_runs", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
    tools=[DuckDuckGo()],
    add_chat_history_to_messages=True,
)
assistant.print_response("How many people live in Canada?")
assistant.print_response("What is their national anthem called?")
