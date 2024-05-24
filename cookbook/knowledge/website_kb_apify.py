from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.pgvector import PgVector2
from phi.assistant import Assistant
from phi.document.reader.website import ApifyWebsiteReader

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# Create a knowledge base with the seed URLs
knowledge_base = WebsiteKnowledgeBase(
    urls=["https://www.zillow.com/homedetails/61600-Palm-Vista-Dr-Joshua-Tree-CA-92252/17499877_zpid/"],
    # Table name: ai.website_documents
    vector_db=PgVector2(
        collection="website_documents",
        db_url=db_url,
    ),
    reader=ApifyWebsiteReader(),
)
# Load the knowledge base
# knowledge_base.load(recreate=True)

# Create an assistant with the knowledge base
assistant = Assistant(
    knowledge_base=knowledge_base,
    add_references_to_prompt=True,
)

# Ask the assistant about the knowledge base
assistant.print_response("How many bedrooms does the house have?")
