# install weaviate - `pip install weaviate-client`

from agno.agent import Agent
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.weaviate import Weaviate

# run weaviate client locally
"""
- Run the docker image: docker pull semitechnologies/weaviate:latest
- Then, run the service:
   docker run -d -p 8080:8080 \
  -v ./data:/var/lib/weaviate \
  semitechnologies/weaviate:latest
"""

vector_db = Weaviate(collection="recipes")
# Create knowledge base
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)
knowledge_base.load(recreate=False)  # Comment out after first run

# Create and use the agent
agent = Agent(
    knowledge=knowledge_base,
    search_knowledge=True,
    show_tool_calls=True,
)
agent.print_response("How to make Thai curry?", markdown=True)
