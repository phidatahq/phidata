from rich.pretty import pprint  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector, SearchType

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
vector_db = PgVector(table_name="recipes", db_url=db_url, search_type=SearchType.hybrid)
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)
# Comment out after first run
# knowledge_base.load(upsert=True)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=vector_db,
    ),
    # Add a tool to search the knowledge base
    search_knowledge=True,
    show_tool_calls=True,
    markdown=True,
)
agent.print_response("How do I make chicken and galangal in Coconut Milk Soup")
