from phi.embedder.ollama import OllamaEmbedder

embedder = OllamaEmbedder(model="openhermes")
embeddings = embedder.get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
