# Import necessary modules
# pip install llama-index-core llama-index-readers-file llama-index-embeddings-openai

from phi.assistant import Assistant
from phi.knowledge.llamaindex import LlamaIndexKnowledgeBase

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)

from llama_index.core.retrievers import VectorIndexRetriever

from llama_index.core.node_parser import SentenceSplitter

import os

import requests

os.makedirs("data\paul_graham", exist_ok=True)


url = "https://raw.githubusercontent.com/run-llama/llama_index/main/docs/docs/examples/data/paul_graham/paul_graham_essay.txt"

file_path = "cookbook\knowledge\data\paul_graham\paul_graham_essay.txt"

response = requests.get(url)

if response.status_code == 200:
    with open(file_path, "wb") as file:
        file.write(response.content)
    print(f"File downloaded and saved as {file_path}")
else:
    print("Failed to download the file")


documents = SimpleDirectoryReader("cookbook\knowledge\data\paul_graham").load_data()

splitter = SentenceSplitter(chunk_size=1024)

nodes = splitter.get_nodes_from_documents(documents)

storage_context = StorageContext.from_defaults()

index = VectorStoreIndex(nodes=nodes, storage_context=storage_context)

retriever = VectorIndexRetriever(index)

# # Create a knowledge base from the vector store
knowledge_base = LlamaIndexKnowledgeBase(retriever=retriever)

# # Create an assistant with the knowledge base
assistant = Assistant(knowledge_base=knowledge_base, search_knowledge=True, debug_mode=True, show_tool_calls=True)

# # Use the assistant to ask a question and print a response.
assistant.print_response("Explain what this text means: low end eats the high end", markdown=True)
