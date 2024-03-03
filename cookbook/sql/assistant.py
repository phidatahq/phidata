from phi.assistant import Assistant
from phi.tools.sql import SQLToolkit

from resources import vector_db  # type: ignore

sql_toolkit = SQLToolkit(db_url=vector_db.get_db_connection_local())

assistant = Assistant(tools=[sql_toolkit], show_tool_calls=True, debug_mode=True)
assistant.print_response("Show me the available databases", markdown=True)
