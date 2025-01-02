# install vespa - `pip install phi-vespa`
from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.vespa import VespaDb
import sys

try:
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

    # Verify Vespa connection
    if not vector_db.is_ready():
        print("Error: Vespa server is not running. Please start Vespa first.")
        sys.exit(1)

    # Create knowledge base
    knowledge_base = PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=vector_db,
    )

    # Load knowledge base with error handling
    try:
        knowledge_base.load(recreate=True)  # Set to False after first successful run
    except Exception as e:
        print(f"Error loading knowledge base: {str(e)}")
        sys.exit(1)

    # Create and use the agent
    agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)

    # Test query to verify everything is working
    try:
        agent.print_response("What are common ingredients in Thai cuisine?", markdown=True)
    except Exception as e:
        print(f"Error querying the agent: {str(e)}")

except Exception as e:
    print(f"Error initializing Vespa: {str(e)}")
    sys.exit(1)
