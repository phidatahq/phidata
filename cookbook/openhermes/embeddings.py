from phi.embedder.ollama import OllamaEmbedder

embedder = OllamaEmbedder(model="openhermes", dimensions=4096)
embeddings = embedder.get_embedding("Embed me")

print(f"Embeddings: {embeddings[:10]}")
print(f"Dimensions: {len(embeddings)}")
