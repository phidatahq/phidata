from phi.embedder.mistral import MistralEmbedder

embedder = MistralEmbedder()

print(embedder.get_embedding("What is the capital of France?"))
