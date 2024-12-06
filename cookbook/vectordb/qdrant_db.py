# pip install qdrant-client 
from phi.vectordb.qdrant import Qdrant
from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase

# run qdrant client locally
"""
- Run the docker image: docker pull qdrant/qdrant
- Then, run the service:
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
"""
COLLECTION_NAME = "thai-recipes"

vector_db = Qdrant(
    collection=COLLECTION_NAME,
    url="http://localhost:6333"
)

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)

knowledge_base.load(recreate=False)  # Comment out after first run

# Create and use the agent
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("List down the ingredients to make Massaman Gai", markdown=True)