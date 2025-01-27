# install weaviate - `pip install weaviate-client`

from phi.agent import Agent
from phi.knowledge.text import TextKnowledgeBase
from phi.vectordb.weaviate import Weaviate

# run weaviate client locally
"""
- Run the docker image: docker pull semitechnologies/weaviate:latest
- Then, run the service:
   docker run -d -p 8080:8080 \
  -v ./data:/var/lib/weaviate \
  semitechnologies/weaviate:latest
"""

vector_db = Weaviate(index_name="weaviate_collection")
# Create knowledge base
knowledge_base = TextKnowledgeBase(
    path="data/txt_files",
    vector_db=vector_db
)

knowledge_base.load(recreate=False)  # Comment out after first run

# Create and use the agent
agent = Agent(knowledge_base=knowledge_base, search_knowledge=True, use_tools=True, show_tool_calls=True)
agent.print_response("How to make Thai curry?", markdown=True)
