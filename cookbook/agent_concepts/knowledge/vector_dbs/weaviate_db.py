"""
Install weaviate using: `pip install weaviate-client`

To use Weaviate Cloud:
1. Sign up for an account at https://console.weaviate.cloud/
2. Create a new cluster and export the following environment variables:
export WCD_URL=***
export WCD_API_KEY=***

To use a local Weaviate instance:
1. Make sure you have docker installed.
2. Run the following command:
docker run -p 8080:8080 -p 50051:50051 cr.weaviate.io/semitechnologies/weaviate:1.28.4
"""

from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.search import SearchType
from agno.vectordb.weaviate import Distance, VectorIndex, Weaviate

vector_db = Weaviate(
    collection="recipes",
    search_type=SearchType.hybrid,
    vector_index=VectorIndex.HNSW,
    distance=Distance.COSINE,
)
# Create knowledge base
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)
knowledge_base.load(recreate=True)  # Comment out after first run

# Create and use the agent
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
    show_tool_calls=True,
)
agent.print_response("How to make Thai curry?", markdown=True)
