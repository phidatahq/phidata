from rich.pretty import pprint  # noqa
from phi.agent import Agent, AgentResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector, SearchType

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
vector_db = PgVector(table_name="recipes", db_url=db_url, search_type=SearchType.hybrid)

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    knowledge=PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=vector_db,
    ),
    enable_rag=True,
    # search_knowledge=True,
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
)
# knowledge_base.load(recreate=True)  # Comment out after first run
# knowledge_base.load(recreate=True, upsert=True)  # Comment out after first run
# knowledge_base.load(upsert=True)  # Comment out after first run

# results = vector_db.vector_search("Gluai Buat Chi")
# print("Vector search results:")
# pprint([r.id for r in results])
#
# results = vector_db.keyword_search("Gluai Buat Chi")
# print("Keyword search results:")
# pprint([r.id for r in results])
#
# results = vector_db.hybrid_search("Gluai Buat Chi")
# print("Hybrid search results:")
# pprint([r.id for r in results])

agent.print_response("How do i make Chicken and Galangal in Coconut Milk Soup")

# run1: AgentResponse = agent.run("How to make Gluai Buat Chi?")  # type: ignore
# pprint(run1)
