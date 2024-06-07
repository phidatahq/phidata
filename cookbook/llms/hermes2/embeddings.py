from phi.embedder.ollama import OllamaEmbedder

embedder = OllamaEmbedder(model="adrienbrault/nous-hermes2pro:Q8_0", dimensions=4096)
embeddings = embedder.get_embedding("Embed me")

print(f"Embeddings: {embeddings[:10]}")
print(f"Dimensions: {len(embeddings)}")
