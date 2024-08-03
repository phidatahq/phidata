from phi.embedder.google import GeminiEmbedder

embeddings = GeminiEmbedder().get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
