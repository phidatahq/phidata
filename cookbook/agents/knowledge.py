from rich.pretty import pprint
from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
vector_db = PgVector(table_name="recipes", db_url=db_url)

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=vector_db,
)

assistant = Agent(
    model=OpenAIChat(model="gpt-4o"),
    knowledge=knowledge_base,
    enable_rag=True,
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
)
# knowledge_base.load(recreate=True)  # Comment out after first run
# knowledge_base.load(recreate=True, upsert=True)  # Comment out after first run
# knowledge_base.load(upsert=True)  # Comment out after first run

results = vector_db.vector_search("Pad Thai")
print("Vector search results:")
pprint([r.id for r in results])

results = vector_db.keyword_search("Pad Thai")
print("Keyword search results:")
pprint([r.id for r in results])

results = vector_db.hybrid_search("Pad Thai")
print("Hybrid search results:")
pprint([r.id for r in results])

# assistant.print_response("How to make Gluai Buat Chi?")

# run1: RunResponse = agent.run("How to make Gluai Buat Chi?")  # type: ignore
# pprint(run1)
