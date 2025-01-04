from phi.assistant import Assistant
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2

knowledge_base = PDFUrlKnowledgeBase(
    # Read PDFs from URLs
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    # Store embeddings in the `ai.recipes` table
    vector_db=PgVector2(
        collection="recipes",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)
# Load the knowledge base
knowledge_base.load(recreate=False)

assistant = Assistant(
    knowledge_base=knowledge_base,
    # The add_references_to_prompt will update the prompt with references from the knowledge base.
    add_references_to_prompt=True,
)
assistant.print_response("How do I make pad thai?", markdown=True)
