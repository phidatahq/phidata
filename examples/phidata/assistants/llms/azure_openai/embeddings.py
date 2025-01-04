from phi.embedder.azure_openai import AzureOpenAIEmbedder

embeddings = AzureOpenAIEmbedder().get_embedding("Embed me")

print(f"Embeddings: {embeddings[:5]}")
print(f"Dimensions: {len(embeddings)}")
