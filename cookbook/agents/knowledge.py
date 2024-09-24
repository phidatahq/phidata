from rich.pretty import pprint
from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(table_name="recipes", db_url=db_url),
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

results = knowledge_base.vector_db.vector_search("Gluai Buat Chi")
print("Vector search results:")
pprint([r.id for r in results])

results = knowledge_base.vector_db.keyword_search("Gluai Buat Chi")
print("Fulltext search results:")
pprint([r.id for r in results])

results = knowledge_base.vector_db.hybrid_search("Gluai Buat Chi")
print("Hybrid search results:")
pprint([r.id for r in results])

# assistant.print_response("How to make Gluai Buat Chi?")

# run1: RunResponse = agent.run("How to make Gluai Buat Chi?")  # type: ignore
# pprint(run1)
