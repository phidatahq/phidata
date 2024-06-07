from phi.assistant import Assistant
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

assistant = Assistant(
    storage=PgAssistantStorage(table_name="recipe_assistant", db_url=db_url),
    knowledge_base=PDFUrlKnowledgeBase(
        urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
        vector_db=PgVector2(collection="recipe_documents", db_url=db_url),
    ),
    # Show tool calls in the response
    show_tool_calls=True,
    # Enable the assistant to search the knowledge base
    search_knowledge=True,
    # Enable the assistant to read the chat history
    read_chat_history=True,
)
# Comment out after first run
assistant.knowledge_base.load(recreate=False)  # type: ignore

assistant.print_response("How do I make pad thai?", markdown=True)
