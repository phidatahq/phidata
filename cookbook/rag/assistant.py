from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2

from resources import vector_db  # type: ignore

# The PDFUrlKnowledgeBase reads PDFs from urls and loads
# the `ai.recipes` table when`knowledge_base.load()` is called.
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(collection="recipes", db_url=vector_db.get_db_connection_local()),
)
knowledge_base.load(recreate=False)

assistant = Assistant(
    knowledge_base=knowledge_base,
    # The add_references_to_prompt flag searches the knowledge base
    # and updates the prompt sent to the LLM.
    add_references_to_prompt=True,
)

assistant.print_response("How do I make pad thai?", markdown=True)
