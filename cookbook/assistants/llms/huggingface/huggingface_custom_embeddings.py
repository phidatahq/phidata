import os

from phi.embedder.huggingface import HuggingfaceCustomEmbedder

embeddings = HuggingfaceCustomEmbedder(api_key=os.getenv("HUGGINGFACE_API_KEY")).get_embedding("Embed me")

print(f"Embeddings: {embeddings}")
print(f"Dimensions: {len(embeddings)}")
