# install vespa - `pip install phi-vespa`

from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.vespa import VespaDb

# Initialize VespaDb
vector_db = VespaDb(
    app_name="recipes",
    url="http://localhost:8080",
    schema={
        "fields": {
            "text": {"type": "string"},
            "embedding": {"type": "tensor(x[384])", "attribute": True},
            "metadata": {"type": "string", "attribute": True}
        }
    }
)

# Create knowledge base
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)

knowledge_base.load(recreate=False)  # Comment out after first run

# Create and use the agent
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("Show me how to make Tom Kha Gai", markdown=True)
