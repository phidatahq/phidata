"""Run `pip install openai psycopg python-docx sqlalchemy` to install dependencies."""

from phi.agent.agent import Agent
from phi.knowledge.docx import DocxKnowledgeBase
from phi.vectordb.pgvector import PgVector
from pathlib import Path

# Create a knowledge base from Docs directory
knowledge_base = DocxKnowledgeBase(
    path=Path("data/docs"),
    vector_db=PgVector(
        table_name="docx_documents",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)


knowledge_base.load()

agent = Agent(
    # Add the knowledge base to the agent
    knowledge=knowledge_base,
    markdown=True,
)

agent.print_response("Please tell me a recipe of an Indian dish", stream=True)
