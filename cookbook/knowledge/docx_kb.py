from pathlib import Path

from phi.agent import Agent
from phi.vectordb.pgvector import PgVector
from phi.knowledge.docx import DocxKnowledgeBase

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Create a knowledge base with the DOCX files from the data/docs directory
knowledge_base = DocxKnowledgeBase(
    path=Path("data/docs"),
    vector_db=PgVector(
        table_name="docx_documents",
        db_url=db_url,
    ),
)
# Load the knowledge base
knowledge_base.load(recreate=False)

# Create an agent with the knowledge base
agent = Agent(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

# Ask the agent about the knowledge base
agent.print_response("Ask me about something from the knowledge base", markdown=True)
