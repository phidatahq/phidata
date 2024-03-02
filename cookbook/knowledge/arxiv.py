from phi.knowledge.arxiv import ArxivKnowledgeBase
from phi.vectordb.pgvector import PgVector2

from resources import vector_db

from phi.assistant import Assistant
from knowledge_base import knowledge_base


knowledge_base = ArxivKnowledgeBase(
    queries=["Generative AI", "Machine Learning"],
    # Table name: ai.arxiv_documents
    vector_db=PgVector2(
        collection="arxiv_documents",
        db_url=vector_db.get_db_connection_local(),
    ),
)

#Creating an assistant with the knowledge base
assistant = Assistant(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

assistant.knowledge_base.load(recreate=False)

assistant.print_response("Ask me about something from the knowledge base",markdown=True)
