import os
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# Initialize Pinecone client
api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key)
index_name = "paul-graham-index"

# Create a Pinecone index
if index_name not in pc.list_indexes():
    pc.create_index(
        name=index_name,
        dimension=1536,  # OpenAI embeddings dimension
        metric="euclidean",  # Distance metric
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

pinecone_index = pc.Index(index_name)

# Set up the data directory
data_dir = Path(__file__).parent.parent.parent.joinpath("wip", "data", "paul_graham")
if not data_dir.is_dir():
    print("Data directory does not exist. Please run the 01_download_text.py script first.")
    exit()

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
vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Create a vector store index from the nodes
index = VectorStoreIndex(nodes=nodes, storage_context=storage_context)
