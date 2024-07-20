# Import necessary modules
# pip install llama-index-core llama-index-readers-file llama-index-retrievers-bm25 llama-index-embeddings-openai llama-index-llms-openai phidata

from pathlib import Path
from shutil import rmtree

import httpx
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.retrievers.bm25 import BM25Retriever

from phi.assistant import Assistant
from phi.knowledge.llamaindex import LlamaIndexKnowledgeBase

# Set up the data directory
data_dir = Path(__file__).parent.parent.parent.joinpath("wip", "data", "paul_graham")
if data_dir.is_dir():
    rmtree(path=data_dir, ignore_errors=True)  # Remove existing directory if it exists
data_dir.mkdir(parents=True, exist_ok=True)  # Create the directory

# Download the text file
url = "https://raw.githubusercontent.com/run-llama/llama_index/main/docs/docs/examples/data/paul_graham/paul_graham_essay.txt"
file_path = data_dir.joinpath("paul_graham_essay.txt")
response = httpx.get(url)
if response.status_code == 200:
    with open(file_path, "wb") as file:
        file.write(response.content)  # Save the downloaded content to a file
    print(f"File downloaded and saved as {file_path}")
else:
    print("Failed to download the file")

# Load the documents from the data directory
documents = SimpleDirectoryReader(str(data_dir)).load_data()

# Create a document store and add the loaded documents
docstore = SimpleDocumentStore()
docstore.add_documents(documents)

# Create a sentence splitter for chunking the text
splitter = SentenceSplitter(chunk_size=1024)

# Split the documents into nodes
nodes = splitter.get_nodes_from_documents(documents)

# Create a storage context
storage_context = StorageContext.from_defaults()

# Create a vector store index from the nodes
index = VectorStoreIndex(nodes=nodes, storage_context=storage_context)

# Set up a query fusion retriever
# This combines vector-based and BM25 retrieval methods
retriever = QueryFusionRetriever(
    [
        index.as_retriever(similarity_top_k=2),  # Vector-based retrieval
        BM25Retriever.from_defaults(docstore=index.docstore, similarity_top_k=2),  # BM25 retrieval
    ],
    num_queries=1,
    use_async=True,
)

# Create a knowledge base from the retriever
knowledge_base = LlamaIndexKnowledgeBase(retriever=retriever)

# Create an assistant with the knowledge base
assistant = Assistant(
    knowledge_base=knowledge_base,
    search_knowledge=True,
    debug_mode=True,
    show_tool_calls=True,
)

# Use the assistant to answer a question and print the response
assistant.print_response("Explain what this text means: low end eats the high end", markdown=True)
