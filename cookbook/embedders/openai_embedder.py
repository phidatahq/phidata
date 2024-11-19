import os

from phi.agent import Agent, AgentKnowledge
from phi.vectordb.pgvector import PgVector
from phi.embedder.openai import OpenAIEmbedder

# Create knowledge base
knowledge_base = AgentKnowledge(
    vector_db=PgVector(
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
        table_name="openai_embeddings",
        embedder=OpenAIEmbedder(
            api_key=os.getenv("OPENAI_API_KEY"),
            dimensions=1536,
        ),
    ),
    num_documents=2,
)

# Add information to the knowledge base
knowledge_base.load_text(
    "This classic spaghetti carbonara combines perfectly cooked al dente pasta "
    "with crispy pancetta and creamy eggs that create a luscious sauce."
)

# Add the knowledge base to the Agent
agent = Agent(knowledge_base=knowledge_base)
