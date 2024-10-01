"""Run `pip install lancedb tantivy` to install dependencies."""

from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.lancedb import LanceDb, SearchType

db_uri = "tmp/lancedb"
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=LanceDb(table_name="recipes", uri=db_uri, search_type=SearchType.vector),
)
# Comment after first run to avoid reloading the knowledge base
# knowledge_base.load(upsert=True)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge_base,
    # Add a tool to search the knowledge base which enables agentic RAG.
    search_knowledge=True,
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
)
agent.print_response("How do I make chicken and galangal in coconut milk soup")
