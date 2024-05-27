import sys
sys.path.append("../phi/embedder")
from azure import AzureOpenAIEmbedder

embedder =  AzureOpenAIEmbedder(    
    api_version = "2024-02-01",
    api_key = "YOUR_API_KEY",
    azure_endpoint = "https://YOUR_RESOURCE_NAME.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT_NAME/embeddings?api-version=2024-02-01",
)

print(embedder.get_embedding_and_usage("hello world"))