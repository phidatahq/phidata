"""
1. Run: `pip install openai lancedb tantivy pypdf sqlalchemy phidata` to install the dependencies
2. Run: `python cookbook/rag/03_traditional_rag_lancedb.py` to run the agent
"""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.embedder.openai import OpenAIEmbedder
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.lancedb import LanceDb, SearchType

# Create a knowledge base of PDFs from URLs
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    # Use LanceDB as the vector database and store embeddings in the `recipes` table
    vector_db=LanceDb(
        table_name="recipes",
        uri="tmp/lancedb",
        search_type=SearchType.vector,
        embedder=OpenAIEmbedder(model="text-embedding-3-small"),
    ),
)
# Load the knowledge base: Comment after first run as the knowledge base is already loaded
knowledge_base.load()

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge_base,
    # Enable RAG by adding references from AgentKnowledge to the user prompt.
    add_context=True,
    # Set as False because Agents default to `search_knowledge=True`
    search_knowledge=False,
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("How do I make chicken and galangal in coconut milk soup", stream=True)
