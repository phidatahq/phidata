import json
from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.agent import AgentKnowledge
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.duckdb import DuckDbTools
from agno.vectordb.pgvector import PgVector
from textwrap import dedent

# ************* Paths *************
cwd = Path(__file__).parent
knowledge_base_dir = cwd.joinpath("knowledge_base")
root_dir = cwd.parent.parent.parent
wip_dir = root_dir.joinpath("wip")
data_dir = wip_dir.joinpath("data")
# Create the wip/data directory if it does not exist
data_dir.mkdir(parents=True, exist_ok=True)
# *******************************

# ************* Storage & Knowledge *************
agent_storage = PostgresAgentStorage(
    schema="ai",
    table_name="viz_agent_sessions",
    db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
)


def get_viz_agent(
    user_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Returns a Data Visualization agent.

    Args:
        data_dir: Directory containing the data files
        user_id: Optional user ID
        debug_mode: Whether to run in debug mode
        initialize_kb: Whether to initialize the knowledge base
    """

    return Agent(
        name="viz_agent",
        user_id=user_id,
        model=OpenAIChat(id="gpt-4o"),
        storage=agent_storage,
        knowledge=AgentKnowledge(
            vector_db=PgVector(
                schema="ai",
                table_name="viz_agent_knowledge",
                embedder=OpenAIEmbedder(),
                db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
            ),
            num_documents=3,  # Retrieve 3 most relevant documents
        ),
        tools=[
            DuckDbTools()
        ],
        show_tool_calls=True,
        read_chat_history=True,
        search_knowledge=True,
        read_tool_call_history=True,
        debug_mode=debug_mode,
        instructions=dedent(f"""\
        You are a data visualization expert focused on writing precise, efficient SQL queries.
        
        When working with DuckDB:
        1. Use `SHOW TABLES` to list available tables
        2. Use `DESCRIBE <table_name>` to see table structure
        3. Write SQL queries without semicolons at the end
        4. Always include a LIMIT clause unless explicitly asked for all results
        
        {dedent(get_viz_agent.__doc__)}
        
        Rules for querying:
        - Always check table existence before querying
        - Verify column names using DESCRIBE
        - Handle NULL values appropriately
        - Account for duplicate records
        - Use proper JOIN conditions
        - Explain your query logic
        - Never use DELETE or DROP statements
        """)
    )
