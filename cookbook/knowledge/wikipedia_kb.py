from phi.assistant import Assistant
from phi.knowledge.wikipedia import WikipediaKnowledgeBase
from phi.vectordb.pgvector import PgVector2

from resources import vector_db  # type: ignore

# Create a knowledge base with the PDFs from the data/pdfs directory
knowledge_base = WikipediaKnowledgeBase(
    topics=["Manchester United", "Real Madrid"],
    # Table name: ai.wikipedia_documents
    vector_db=PgVector2(
        collection="wikipedia_documents",
        db_url=vector_db.get_db_connection_local(),
    ),
)
# Load the knowledge base
knowledge_base.load(recreate=False)

# Create an assistant with the knowledge base
assistant = Assistant(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

# Ask the assistant about the knowledge base
assistant.print_response("Which team is objectively better, Manchester United or Real Madrid?")
