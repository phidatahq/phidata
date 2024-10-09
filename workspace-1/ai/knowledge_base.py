from phi.embedder.openai import OpenAIEmbedder
from phi.knowledge.combined import CombinedKnowledgeBase
from phi.knowledge.pdf import PDFUrlKnowledgeBase, PDFKnowledgeBase
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.pgvector import PgVector2

from ai.settings import ai_settings
from db.session import db_url

pdf_knowledge_base = CombinedKnowledgeBase(
    sources=[
        PDFUrlKnowledgeBase(urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"]),
        PDFKnowledgeBase(path="data/pdfs"),
    ],
    vector_db=PgVector2(
        db_url=db_url,
        # Store the embeddings in ai.pdf_documents
        collection="pdf_documents",
        embedder=OpenAIEmbedder(model=ai_settings.embedding_model),
    ),
    # 2 references are added to the prompt
    num_documents=2,
)

website_knowledge_base = WebsiteKnowledgeBase(
    # Add URLs to the knowledge base
    # urls=["https://docs.phidata.com/introduction"],
    max_depth=1,
    # Number of links to follow from the seed URLs
    max_links=15,
    vector_db=PgVector2(
        db_url=db_url,
        # Store the embeddings in ai.website_documents
        collection="website_documents",
        embedder=OpenAIEmbedder(model=ai_settings.embedding_model),
    ),
    # 3 references are added to the prompt
    num_documents=3,
)
