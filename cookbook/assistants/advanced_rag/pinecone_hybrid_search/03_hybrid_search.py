import os

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.pinecone import PineconeVectorStore

from pinecone import Pinecone

from phi.assistant import Assistant
from phi.knowledge.llamaindex import LlamaIndexKnowledgeBase

# Initialize Pinecone client
api_key = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=api_key)
index_name = "paul-graham-index"

# Ensure that the index exists
if index_name not in pc.list_indexes():
    print("Pinecone index does not exist. Please run the 02_upsert_pinecone.py script first.")
    exit()

# Initialize Pinecone index
pinecone_index = pc.Index(index_name)
vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
index = VectorStoreIndex.from_vector_store(vector_store)

# Create Hybrid Retriever
retriever = QueryFusionRetriever(
    [
        index.as_retriever(similarity_top_k=10),  # Vector-based retrieval
        BM25Retriever.from_defaults(docstore=index.docstore, similarity_top_k=10),  # BM25 keyword retrieval
    ],
    num_queries=3,
    use_async=True,
)

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
