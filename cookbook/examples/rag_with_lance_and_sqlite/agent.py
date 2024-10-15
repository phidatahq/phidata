"""Run `pip install lancedb` to install dependencies."""

from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.lancedb import LanceDb
from phi.embedder.ollama import OllamaEmbedder
from phi.agent import Agent
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.model.ollama import Ollama

# Define the database URL where the vector database will be stored
db_url = "/tmp/lancedb"

# Configure the language model
model = Ollama(model="llama3:8b", temperature=0.0)

# Create Ollama embedder
embedder = OllamaEmbedder(model="nomic-embed-text", dimensions=768)

# Create the vector database
vector_db = LanceDb(
    table_name="recipes",  # Table name in the vector database
    uri=db_url,  # Location to initiate/create the vector database
    embedder=embedder,  # Without using this, it will use OpenAI embeddings by default
)

# Create a knowledge base from a PDF URL using LanceDb for vector storage and OllamaEmbedder for embedding
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)

# Load the knowledge base without recreating it if it already exists in Vector LanceDB
knowledge_base.load(recreate=False)
# agent.knowledge_base.load(recreate=False) # You can also use this to load a knowledge base after creating agent

# Set up SQL storage for the agent's data
storage = SqlAgentStorage(table_name="recipes", db_file="data.db")
storage.create()  # Create the storage if it doesn't exist

# Initialize the Agent with various configurations including the knowledge base and storage
agent = Agent(
    session_id="session_id",  # use any unique identifier to identify the run
    user_id="user",  # user identifier to identify the user
    model=model,
    knowledge=knowledge_base,
    storage=storage,
    show_tool_calls=True,
    debug_mode=True,  # Enable debug mode for additional information
)

# Use the agent to generate and print a response to a query, formatted in Markdown
agent.print_response("What is the first step of making Gluai Buat Chi from the knowledge base?", markdown=True)
