from phi.embedder.anyscale import AnyscaleEmbedder

embeddings = AnyscaleEmbedder().get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
