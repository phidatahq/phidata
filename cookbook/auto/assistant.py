from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector

from resources import vector_db  # type: ignore

knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://www.family-action.org.uk/content/uploads/2019/07/meals-more-recipes.pdf"],
    vector_db=PgVector(collection="recipes", db_url=vector_db.get_db_connection_local()),
)
knowledge_base.load(recreate=False)

assistant = Assistant(
    knowledge_base=knowledge_base,
    use_tools=True,
    show_tool_calls=True,
)

assistant.print_response("How do I make chicken tikka salad?")
assistant.print_response("What was my last question?")
