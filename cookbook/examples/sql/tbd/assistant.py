from phi.assistant import Assistant
from phi.tools.sql import SQLToolkit
from phi.knowledge.json import JSONKnowledgeBase
from phi.vectordb.pgvector import PgVector2

from resources import vector_db  # type: ignore

sql_toolkit = SQLToolkit(db_url=vector_db.get_db_connection_local())


knowledge_base = JSONKnowledgeBase(
    path="data",
    vector_db=PgVector2(
        collection="task_document_json",
        db_url=vector_db.get_db_connection_local(),
    ),
    num_documents=5,
)
knowledge_base.load(recreate=True, upsert=True)

assistant = Assistant(
    tools=[sql_toolkit],
    show_tool_calls=True,
    debug_mode=True,
    description="You are a SQL Assistant and your goal is to help users interact with a SQL database. You use PostgreSQL as your database and you interact with it using SQLAlchemy.",
    instructions=[
        "Use get_table_names to get a list of table names you have access to.",
        "Use run_sql_query to run a SQL query that does not requre an output. For example: CREATE",
        "Use run run_sql_query_and_get_result to run a SQL query that retutns an output. For example: SELECT * FROM table",
        "If asked to interact with a table that already exists, use the function describe_table to get the schema of the table.",
    ],
    knowledge_base=knowledge_base,
)

assistant.print_response("Can you show me the contents of task_document_json table?", markdown=True)
