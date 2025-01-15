import os
from os import getenv
from agno.agent import Agent
from agno.knowledge.youtube import YouTubeKnowledgeBase, YouTubeReader
from agno.vectordb.qdrant import Qdrant
from agno.vectordb.pgvector.pgvector import PgVector

api_key = getenv("QDRANT_API_KEY")
qdrant_url = getenv("QDRANT_URL")

vector_db = Qdrant(collection="youtube-phidata", url=qdrant_url, api_key=api_key)

# Create a knowledge base with the PDFs from the data/pdfs directory
knowledge_base = YouTubeKnowledgeBase(
    urls=["https://www.youtube.com/watch?v=CDC3GOuJyZ0"],
    vector_db=vector_db,
    reader=YouTubeReader(chunk=True),
)
knowledge_base.load(recreate=False)  # only once, comment it out after first run

agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
)

agent.print_response("what is the major focus of the knowledge provided?", markdown=True)