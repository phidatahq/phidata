import json
from typing import Optional
from textwrap import dedent
from pathlib import Path

from phi.assistant import Assistant
from phi.tools.sql import SQLTools
from phi.tools.file import FileTools
from phi.llm.openai import OpenAIChat
from phi.embedder.openai import OpenAIEmbedder
from phi.knowledge.json import JSONKnowledgeBase
from phi.knowledge.text import TextKnowledgeBase
from phi.knowledge.combined import CombinedKnowledgeBase
from phi.vectordb.pgvector import PgVector2
from phi.storage.assistant.postgres import PgAssistantStorage


# ************* Database Connection *************
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
# *******************************

# ************* Paths *************
cwd = Path(__file__).parent
knowledge_base_dir = cwd.joinpath("knowledge_base")
root_dir = cwd.parent.parent.parent
wip_dir = root_dir.joinpath("wip")
sql_queries_dir = wip_dir.joinpath("queries")
# Create the wip/queries directory if it does not exist
sql_queries_dir.mkdir(parents=True, exist_ok=True)
# *******************************

# ************* Storage & Knowledge *************
assistant_storage = PgAssistantStorage(
    schema="ai",
    # Store assistant runs in ai.sql_assistant_runs table
    table_name="sql_assistant_runs",
    db_url=db_url,
)
assistant_knowledge = CombinedKnowledgeBase(
    sources=[
        # Reads text files, SQL files, and markdown files
        TextKnowledgeBase(
            path=cwd.joinpath("knowledge"),
            formats=[".txt", ".sql", ".md"],
        ),
        # Reads JSON files
        JSONKnowledgeBase(path=cwd.joinpath("knowledge")),
    ],
    # Store assistant knowledge base in ai.sql_assistant_knowledge table
    vector_db=PgVector2(
        schema="ai",
        collection="sql_assistant_knowledge",
        db_url=db_url,
        embedder=OpenAIEmbedder(model="text-embedding-3-small", dimensions=1536),
    ),
    # 5 references are added to the prompt
    num_documents=5,
)
# *******************************

# ************* Semantic Model *************
# This semantic model helps the assistant understand the tables and columns it can use
semantic_model = {
    "tables": [
        {
            "table_name": "constructors_championship",
            "table_description": "Contains data for the constructor's championship from 1958 to 2020, capturing championship standings from when it was introduced.",
            "Use Case": "Use this table to get data on constructor's championship for various years or when analyzing team performance over the years.",
        },
        {
            "table_name": "drivers_championship",
            "table_description": "Contains data for driver's championship standings from 1950-2020, detailing driver positions, teams, and points.",
            "Use Case": "Use this table to access driver championship data, useful for detailed driver performance analysis and comparisons over years.",
        },
        {
            "table_name": "fastest_laps",
            "table_description": "Contains data for the fastest laps recorded in races from 1950-2020, including driver and team details.",
            "Use Case": "Use this table when needing detailed information on the fastest laps in Formula 1 races, including driver, team, and lap time data.",
        },
        {
            "table_name": "race_results",
            "table_description": "Holds comprehensive race data for each Formula 1 race from 1950-2020, including positions, drivers, teams, and points.",
            "Use Case": "This table is ideal for querying detailed results of each race, including driver standings, teams, and performance metrics across all races.",
        },
        {
            "table_name": "race_wins",
            "table_description": "Documents race win data from 1950-2020, detailing venue, winner, team, and race duration.",
            "Use Case": "Use this table for retrieving data on race winners, their teams, and race conditions, suitable for analysis of race outcomes and team success.",
        },
    ]
}
# *******************************


def get_sql_assistant(
    run_id: Optional[str] = None,
    user_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    """Returns a Sql Assistant."""

    return Assistant(
        name="sql_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=OpenAIChat(model="gpt-4o", temperature=0),
        storage=assistant_storage,
        knowledge_base=assistant_knowledge,
        show_tool_calls=True,
        read_chat_history=True,
        search_knowledge=True,
        read_tool_call_history=True,
        tools=[SQLTools(db_url=db_url), FileTools(base_dir=sql_queries_dir)],
        debug_mode=debug_mode,
        add_chat_history_to_messages=True,
        num_history_messages=4,
        description="You are a SQL expert called `SQrL` and your goal is to analyze data stored in a PostgreSQL database.",
        instructions=[
            "When a user messages you, determine if you need query the database or can respond directly.",
            "If you need to run a query, identify the tables you need to query from the `semantic_model` provided below.",
            "IMPORTANT: ALWAYS use the `search_knowledge_base` tool with the table name as input to get table metadata and rules.",
            "Then, **THINK STEP BY STEP** about how you will write the query. Do not rush into writing a query."
            "Once you have mapped out a **CHAIN OF THOUGHT**, start the process of writing a query.",
            "Using the table information and rules, create one single syntactically correct PostgreSQL query to accomplish your task.",
            "If the `search_knowledge_base` tool returns example queries, use them as a reference.",
            "If you need more information about the table, use the `describe_table` tool.",
            "REMEMBER: ALWAYS FOLLOW THE TABLE RULES. NEVER IGNORE THEM. IT IS CRITICAL THAT YOU FOLLOW THE `table rules` if provided.",
            "If you need to join tables, check the `semantic_model` for the relationships between the tables."
            + "\n  - If the `semantic_model` contains a relationship between tables, use that relationship to join the tables even if the column names are different."
            + "\n  - If you cannot find a relationship in the `semantic_model`, use `describe_table` and only join on the columns that have the same name and data type."
            + "\n  - If you cannot find a valid relationship, ask the user to provide the column name to join.",
            "If you cannot find relevant tables, columns or relationships, stop and ask the user for more information.",
            "Once you have a syntactically correct query, run it using the `run_sql_query` function.",
            "When running a query:"
            + "\n  - Do not add a `;` at the end of the query."
            + "\n  - Always provide a limit unless the user explicitly asks for all results.",
            "After you run the query, analyse the results and return the answer in markdown format.",
            "Always show the user the SQL you ran to get the answer.",
            "Continue till you have accomplished the task.",
            "Show results as a table or a chart if possible.",
            "If the users asks about the tables you have access to, simply share the table names from the `semantic_model`.",
        ],
        add_to_system_prompt=dedent(
            f"""
Additional set of guidelines that you MUST follow:
<rules>
- You must always get table information from your knowledge base before writing a query.
- Do not use phrases like "based on the information provided" or "from the knowledge base".
- Never mention that you are using example queries from the knowledge base.
- Always show the SQL queries you use to get the answer.
- Make sure your query accounts for duplicate records.
- Make sure your query accounts for null values.
- If you run a query, explain why you ran it.
- **NEVER, EVER RUN CODE TO DELETE DATA OR ABUSE THE LOCAL SYSTEM**
- ALWAYS FOLLOW THE `table rules` if provided. NEVER IGNORE THEM.
</rules>

The following `semantic_model` contains information about tables and the relationships between them:
<semantic_model>
{json.dumps(semantic_model, indent=4)}
</semantic_model>

After finishing your task, ask the user relevant followup questions like "was the result okay, would you like me to fix any problems?"
If the user says yes, get the previous query using the `get_tool_call_history(num_calls=3)` function and fix the problems.
If the user wants to see the SQL, get it using the `get_tool_call_history(num_calls=3)` function.
"""
        ),
    )
