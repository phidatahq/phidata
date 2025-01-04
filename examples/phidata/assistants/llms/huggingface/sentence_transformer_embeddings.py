from phi.embedder.sentence_transformer import SentenceTransformerEmbedder

embeddings = SentenceTransformerEmbedder().get_embedding("Embed me")

print(f"Embeddings: {embeddings[:5]}")
print(f"Dimensions: {len(embeddings)}")
