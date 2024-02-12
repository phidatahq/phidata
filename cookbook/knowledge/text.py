from phi.knowledge.text import TextKnowledgeBase
from phi.vectordb.pgvector import PgVector2
from phi.assistant import Assistant
from resources import vector_db
from knowledge_base import knowledge_base
from pathlib import Path


# Initialize the TextKnowledgeBase
knowledge_base = TextKnowledgeBase(
    path=Path("data/docs"),  # Table name: ai.text_documents
    vector_db=PgVector2(
        collection="text_documents",
        db_url=vector_db.get_db_connection_local(),
    ),
    formats=[".txt"],  # Formats accepted by this knowledge base
    num_documents=5,  # Number of documents to return on search
    optimize_on=10,  # Number of documents to optimize the vector db on
)

# Initialize the Assistant with the knowledge_base
assistant = Assistant(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

# Load the knowledge base
assistant.knowledge_base.load(recreate=False)

# Use the assistant
assistant.print_response("Ask me about something from the knowledge base",markdown=True)
