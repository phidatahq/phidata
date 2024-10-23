"""Run `pip install duckduckgo-search sqlalchemy pgvector pypdf anthropic openai` to install dependencies."""

from phi.agent import Agent
from phi.model.anthropic import Claude
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(table_name="recipes", db_url=db_url),
)
knowledge_base.load(recreate=True)  # Comment out after first run

agent = Agent(
    model=Claude(id="claude-3-5-sonnet-20241022"),
    knowledge_base=knowledge_base,
    use_tools=True,
    show_tool_calls=True,
    debug_mode=True,
)
agent.print_response("How to make Thai curry?", markdown=True)
