from phi.embedder.together import TogetherEmbedder

embeddings = TogetherEmbedder().get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
