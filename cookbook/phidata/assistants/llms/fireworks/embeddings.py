from phi.embedder.fireworks import FireworksEmbedder

embeddings = FireworksEmbedder().get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
