from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector, SearchType

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
knowledge_base = PDFUrlKnowledgeBase(
    # Read PDF from this URL
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    # Store embeddings in the `ai.recipes` table
    vector_db=PgVector(table_name="recipes", db_url=db_url, search_type=SearchType.hybrid),
)
# Load the knowledge base: Comment after first run
knowledge_base.load(upsert=True)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge_base,
    # Enable RAG by adding references from AgentKnowledge to the user prompt.
    enable_rag=True,
    # Set as False because Agents default to `search_knowledge=True`
    search_knowledge=False,
    markdown=True,
    # debug_mode=True,
)
agent.print_response("How do I make chicken and galangal in coconut milk soup", stream=True)
