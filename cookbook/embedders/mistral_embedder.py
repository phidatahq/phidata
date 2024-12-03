from phi.agent import AgentKnowledge
from phi.vectordb.pgvector import PgVector
from phi.embedder.mistral import MistralEmbedder

embeddings = MistralEmbedder().get_embedding("The quick brown fox jumps over the lazy dog.")

# Print the embeddings and their dimensions
print(f"Embeddings: {embeddings[:5]}")
print(f"Dimensions: {len(embeddings)}")

# Example usage:
knowledge_base = AgentKnowledge(
    vector_db=PgVector(
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
        table_name="mistral_embeddings",
        embedder=MistralEmbedder(),
    ),
    num_documents=2,
)
