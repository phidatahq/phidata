from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2

from resources import vector_db

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector2(
        collection="recipes",
        db_url=vector_db.get_db_connection_local()
    ),
)
# Comment out as the knowledge base is already loaded.
# knowledge_base.load(recreate=False)

assistant = Assistant(
    knowledge_base=knowledge_base,
    # Show tool calls in the response
    show_tool_calls=True,
    # Enable the assistant to search the knowledge base
    search_knowledge=True,
    # Enable the assistant to read the chat history
    read_chat_history=True,
)
assistant.print_response("How do I make pad thai?", markdown=True)
assistant.print_response("What was my last question?", markdown=True)
