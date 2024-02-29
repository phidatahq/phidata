from phi.knowledge.wikipedia import WikipediaKnowledgeBase
from phi.vectordb.pgvector import PgVector2
from phi.assistant import Assistant

from resources import vector_db

knowledge_base = WikipediaKnowledgeBase(
    topics=["Manchester United", "Real Madrid"],
    # Table name: ai.wikipedia_documents
    vector_db=PgVector2(
        collection="wikipedia_documents",
        db_url=vector_db.get_db_connection_local(),
    ),
)

assistant = Assistant(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

assistant.knowledge_base.load(recreate=False)

assistant.print_response("Which team is objectively better, Manchester United or Real Madrid?")
