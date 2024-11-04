from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.redis import RedisVector

redis_url = "paste your redis url here"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=RedisVector(redis_url=redis_url),
)
knowledge_base.load(recreate=False)  # Comment out after first run

agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("How to make Thai curry?", markdown=True)
