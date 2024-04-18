from phi.embedder.ollama import OllamaEmbedder

embedder = OllamaEmbedder(model="nomic-embed-text")
embeddings = embedder.get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
