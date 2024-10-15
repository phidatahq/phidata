from phi.agent import Agent
from phi.knowledge.arxiv import ArxivKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Create a knowledge base with the ArXiv documents
knowledge_base = ArxivKnowledgeBase(
    queries=["Generative AI", "Machine Learning"],
    # Table name: ai.arxiv_documents
    vector_db=PgVector(
        table_name="arxiv_documents",
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
