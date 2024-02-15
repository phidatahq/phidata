from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.pgvector import PgVector2
from phi.assistant import Assistant
from resources import vector_db


knowledge_base = WebsiteKnowledgeBase(
    urls=["https://docs.phidata.com/introduction"], 
    # Number of links to follow from the seed URLs
    max_links=10,
    # Table name: ai.website_documents
    vector_db=PgVector2(
        collection="website_documents",
        db_url=vector_db.get_db_connection_local(),
    ),
)

# Make an assistant for above knowledge base
assistant = Assistant(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

assistant.knowledge_base.load(recreate=False)

assistant.print_response("How does phidata work?")
