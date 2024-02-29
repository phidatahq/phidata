from phi.embedder.openai import OpenAIEmbedder

embeddings = OpenAIEmbedder().get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
