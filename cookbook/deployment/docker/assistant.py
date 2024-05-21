import os

from phi.assistant import Assistant
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2

db_url = os.getenv("DB_URL", default="postgresql+psycopg2://ai:ai@pgvector:5432/ai")

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(collection="recipes", db_url=db_url),
)
# Comment out after first run
knowledge_base.load(recreate=True)

storage = PgAssistantStorage(table_name="pdf_assistant", db_url=db_url)


assistant = Assistant(
    knowledge_base=knowledge_base,
    storage=storage,
    # tool_calls=True adds functions to
    # search the knowledge base and chat history
    use_tools=True,
    show_tool_calls=True,
    # Uncomment the following line to use traditional RAG
    # add_references_to_prompt=True,
)

assistant.print_response("Tell me about soups", markdown=True)