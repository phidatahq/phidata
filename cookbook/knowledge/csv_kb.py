from pathlib import Path

from phi.agent import Agent
from phi.knowledge.csv import CSVKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"


knowledge_base = CSVKnowledgeBase(
    path=Path("data/csvs"),
    vector_db=PgVector(
        table_name="csv_documents",
        db_url=db_url,
    ),
    num_documents=5,  # Number of documents to return on search
)
# Load the knowledge base
knowledge_base.load(recreate=False)

# Initialize the Agent with the knowledge_base
agent = Agent(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

# Use the agent
agent.print_response("Ask me about something from the knowledge base", markdown=True)
