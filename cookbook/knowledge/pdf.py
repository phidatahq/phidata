# Knowledge base dependencies 
from phi.knowledge.pdf import PDFKnowledgeBase, PDFReader
from phi.vectordb.pgvector import PgVector2 
from resources import vector_db 
# Assistant dependencies 
from phi.assistant import Assistant


# Setting up knowledge base. 
pdf_knowledge_base = PDFKnowledgeBase(
    path = "data/pdfs",
    vector_db = PgVector2(
        collection = "pdf_documents", 
        db_url = vector_db.get_db_connection_local(),
    ),
    reader = PDFReader(chunk=True),
)
# Instantiating an assistant to use the knowledge base 
assistant = Assistant(
    knowledge_base = pdf_knowledge_base,
    add_references_to_prompt = True,
)

# reference to database
print(vector_db.get_db_connection_local()) # can inspect database further via psql e.g. "psql -h localhost -p 5432 -U ai -d ai"

#calling assistant 
assistant.knowledge_base.load(recreate=False)
assistant.print_response("what are the building hints from the lego building book?")





