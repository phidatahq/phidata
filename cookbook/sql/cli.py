from phi.assistant import Assistant
from phi.tools.sql import SQLToolkit

from resources import vector_db  # type: ignore

sql_toolkit = SQLToolkit(db_url=vector_db.get_db_connection_local())

assistant = Assistant(
    tools=[sql_toolkit],
    show_tool_calls=True,
    description="You are a SQL Assistant and your goal is to help users interact with a SQL database.",
    instructions=[
        "Before modifying the SQL database, confirm with the user that they want to proceed.",
    ],
    debug_mode=True,
    add_chat_history_to_messages=True,
    num_history_messages=6,
)

assistant.cli_app(markdown=True)
# - Show me the available tables
# - Create a table of students with columns student_id, course, semester, subject, score
# - Add some sample data to the students table
