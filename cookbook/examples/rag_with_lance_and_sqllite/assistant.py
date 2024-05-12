# Import necessary modules from the phi library
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.lancedb.lancedb import LanceDb
from phi.embedder.ollama import OllamaEmbedder
from phi.assistant import Assistant
from phi.storage.assistant.sqllite import SqlAssistantStorage
from phi.llm.ollama import Ollama

# Define the database URL where the vector database will be stored
db_url = "/tmp/lancedb"

# Configure the language model
llm = Ollama(model="llama3:8b", temperature=0.0)

# Create Ollama embedder
embedder = OllamaEmbedder(model="nomic-embed-text", dimensions=768)

# Create the vectore database
vector_db = LanceDb(
    table_name="recipes",  # Table name in the vectore database
    uri=db_url,  # Location to initiate/create the vector database
    embedder=embedder,  # Without using this, it will use OpenAI embeddings by default
)

# Create a knowledge base from a PDF URL using LanceDb for vector storage and OllamaEmbedder for embedding
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)

# Load the knowledge base without recreating it if it already exists in Vectore LanceDB
knowledge_base.load(recreate=False)
# assistant.knowledge_base.load(recreate=False) # You can also use this to load a knowledge base after creating assistant

# Set up SQL storage for the assistant's data
storage = SqlAssistantStorage(table_name="recipies", db_file="data.db")
storage.create()  # Create the storage if it doesn't exist

# Initialize the Assistant with various configurations including the knowledge base and storage
assistant = Assistant(
    run_id="run_id",  # use any unique identifier to identify the run
    user_id="user",  # user identifier to identify the user
    llm=llm,
    knowledge_base=knowledge_base,
    storage=storage,
    tool_calls=True,  # Enable function calls for searching knowledge base and chat history
    use_tools=True,
    show_tool_calls=True,
    search_knowledge=True,
    add_references_to_prompt=True,  # Use traditional RAG (Retrieval-Augmented Generation)
    debug_mode=True,  # Enable debug mode for additional information
)

# Use the assistant to generate and print a response to a query, formatted in Markdown
assistant.print_response("What is the first step of making Gluai Buat Chi from the knowledge base?", markdown=True)
