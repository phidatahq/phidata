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
        tools=[DuckDbTools()],
        show_tool_calls=True,
        read_chat_history=True,
        search_knowledge=True,
        read_tool_call_history=True,
        debug_mode=debug_mode,
        description="""You are a Data Visualization expert called `VizWiz`. Your goal is to help users understand and analyze their data.
You can help users with:
- Understanding data distributions and patterns
- Finding relationships between variables
- Identifying trends and outliers
- Basic statistical analysis
- Data quality assessment""",
        instructions=[
            "1 You need to search the knowledge base"
            "2 you will get data from knowledge_base"
            "3. use duckdb tools to answer the question"
        ],
    )
