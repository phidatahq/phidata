# install upstash-vector - `pip install upstash-vector`

from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.upstash import Upstash
from phi.embedder.openai import OpenAIEmbedder

# OPENAI_API_KEY must be set in the environment
VECTOR_DB_DIMENSION = 1536

# How to connect to an Upstash Vector index
# - Create a new index in Upstash Console with the correct dimension
# - Fetch the URL and token from Upstash Console
# - Replace the values below or use environment variables

# Initialize Upstash DB
vector_db = Upstash(
    url="UPSTASH_VECTOR_REST_URL",
    token="UPSTASH_VECTOR_REST_TOKEN",
    dimension=VECTOR_DB_DIMENSION,
    embedder=OpenAIEmbedder(dimensions=VECTOR_DB_DIMENSION),
)

# Create a new PDFUrlKnowledgeBase
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)

# Load the knowledge base - after first run, comment out
knowledge_base.load(recreate=False, upsert=True)

# Create and use the agent
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("What are some tips for cooking glass noodles?", markdown=True)
