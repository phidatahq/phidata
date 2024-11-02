from typing import List, Any, Optional  
import redis
from hashlib import md5
import numpy as np  

from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance
from phi.utils.log import logger


class RedisDb(VectorDb):
    def __init__(
        self,
        collection: str,
        embedder: Embedder = OpenAIEmbedder(),
        distance: Distance = Distance.cosine,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        **kwargs,
    ):
        self.collection = collection
        self.embedder = embedder
        self.distance = distance
        self.host = host
        self.port = port
        self.db = db
        self.client = redis.StrictRedis(host=self.host, port=self.port, db=self.db, **kwargs)

    def create(self) -> None:
        """Initialize the collection in Redis if not exists."""
        if not self.exists():
            logger.debug(f"Creating collection: {self.collection}")
            self.client.sadd("collections", self.collection)
        else:
            logger.debug(f"Collection already exists: {self.collection}")

    def doc_exists(self, document: Document) -> bool:
        """Check if a document exists in the collection."""
        doc_id = md5(document.content.encode()).hexdigest()
        return self.client.hexists(self.collection, doc_id)

    def insert(self, documents: List[Document], filters: Optional[dict[str, Any]] = None) -> None:
        """Insert documents into the collection."""
        logger.debug(f"Inserting {len(documents)} documents")
        for document in documents:
            document.embed(embedder=self.embedder)
            doc_id = md5(document.content.encode()).hexdigest()
            self.client.hset(self.collection, doc_id, document.content)
            logger.debug(f"Inserted document: {document.id} | {document.name}")

    def upsert(self, documents: List[Document], filters: Optional[dict[str, Any]] = None) -> None:
        """Upsert documents into the collection."""
        logger.debug(f"Upserting {len(documents)} documents")
        for document in documents:
            document.embed(embedder=self.embedder)
            doc_id = md5(document.content.encode()).hexdigest()
            self.client.hset(self.collection, doc_id, document.content)
            logger.debug(f"Upserted document: {document.id} | {document.name}")

    def search(self, query: str, limit: int = 5, filters: Optional[dict[str, Any]] = None) -> List[Document]:
        """Search for a query in the collection."""
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        logger.debug("Performing a basic search (not optimized for embeddings)")
        # Retrieve all document contents
        results = self.client.hvals(self.collection)

        # Calculate similarities and store in a list
        similarities = []
        for result in results:
            document_content = result.decode("utf-8")
            document_embedding = self.embedder.get_embedding(document_content)
            if document_embedding is not None:
                similarity = self.calculate_similarity(query_embedding, document_embedding)
                similarities.append((similarity, Document(content=document_content)))

        # Sort results by similarity and limit to top 'limit' results
        similarities.sort(key=lambda x: x[0], reverse=True)
        search_results = [doc for _, doc in similarities[:limit]]
        return search_results

    def calculate_similarity(self, query_embedding: np.ndarray, document_embedding: np.ndarray) -> float:
        """Calculate the cosine similarity between two embeddings."""
        dot_product = np.dot(query_embedding, document_embedding)
        norm_query = np.linalg.norm(query_embedding)
        norm_document = np.linalg.norm(document_embedding)
        if norm_query == 0 or norm_document == 0:
            return 0.0  # Handle zero vectors to avoid division by zero
        return dot_product / (norm_query * norm_document)

    def delete(self) -> bool:  # Change return type to bool
        """Delete the collection from Redis."""
        if self.exists():
            logger.debug(f"Deleting collection: {self.collection}")
            self.client.delete(self.collection)
            return True
        return False  # Return False if collection does not exist

    def exists(self) -> bool:
        """Check if the collection exists in Redis."""
        return self.client.sismember("collections", self.collection)

    def get_count(self) -> int:
        """Get the count of documents in the collection."""
        if self.exists():
            return self.client.hlen(self.collection)
        return 0
