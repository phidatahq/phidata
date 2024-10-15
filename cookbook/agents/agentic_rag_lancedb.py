"""Run `pip install openai lancedb tantivy` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.lancedb import LanceDb, SearchType

db_uri = "tmp/lancedb"
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=LanceDb(table_name="recipes", uri=db_uri, search_type=SearchType.vector),
)
# Load the knowledge base: Comment out after first run
knowledge_base.load(upsert=True)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge_base,
    # Add a tool to read chat history.
    read_chat_history=True,
    show_tool_calls=True,
    markdown=True,
    # debug_mode=True,
)
agent.print_response("How do I make chicken and galangal in coconut milk soup", stream=True)
