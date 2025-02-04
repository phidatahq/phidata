import json
import uuid
from hashlib import md5
from os import getenv
from typing import Any, Dict, List, Optional

try:
    import weaviate
    from weaviate.classes.config import Configure, DataType, Property
    from weaviate.classes.init import Auth
    from weaviate.classes.query import Filter
except ImportError:
    raise ImportError("Weaviate is not installed. Install using 'pip install weaviate-client'.")

from agno.document import Document
from agno.embedder import Embedder
from agno.reranker.base import Reranker
from agno.utils.log import logger
from agno.vectordb.base import VectorDb
from agno.vectordb.distance import Distance
from agno.vectordb.search import SearchType


class Weaviate(VectorDb):
    """
    Weaviate class for managing vector operations with Weaviate vector database (v4 client).
    """

    def __init__(
        self,
        wcd_url: Optional[str] = None,
        wcd_api_key: Optional[str] = None,
        client: Optional[weaviate.WeaviateClient] = None,
        collection: str = "default",
        embedder: Optional[Embedder] = None,
        search_type: SearchType = SearchType.vector,
        distance: Distance = Distance.cosine,
        reranker: Optional[Reranker] = None,
    ):
        """
        Initialize the Weaviate instance.

        Args:
            client (weaviate.WeaviateClient): The Weaviate client instance.
            collection (str): The name of the Weaviate collection (class).
            embedder (Optional[Embedder]): Embedder instance for creating embeddings.
            search_type (SearchType): Type of search to perform.
            distance (Distance): Distance metric for vector comparisons.
            reranker (Optional[Reranker]): Reranker instance for search results.
        """
        self.client = client
        self.collection = collection

        # Embedder for embedding the document contents
        if embedder is None:
            from agno.embedder.openai import OpenAIEmbedder

            embedder = OpenAIEmbedder()

        self.embedder: Embedder = embedder
        self.dimensions: Optional[int] = self.embedder.dimensions

        self.wcd_url = wcd_url or getenv("WCD_URL")
        self.wcd_api_key = wcd_api_key or getenv("WCD_API_KEY")

        if self.dimensions is None:
            raise ValueError("Embedder.dimensions must be set.")

        # Search type
        self.search_type: SearchType = search_type
        # Distance metric
        self.distance: Distance = distance

        # Reranker instance
        self.reranker: Optional[Reranker] = reranker

        logger.debug(f"Initialized Weaviate with collection: '{self.collection}'")

    def get_client(self) -> weaviate.WeaviateClient:
        """Initialize and return a Weaviate client instance.

        Attempts to create a client using WCD (Weaviate Cloud Deployment) credentials if provided,
        otherwise falls back to local connection. Maintains a singleton pattern by reusing
        an existing client if already initialized.

        Returns:
            weaviate.WeaviateClient: An initialized Weaviate client instance.
        """
        if self.client is not None:
            return self.client

        if self.wcd_url and self.wcd_api_key:
            logger.info("Initializing Weaviate Cloud client")
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.wcd_url, auth_credentials=Auth.api_key(self.wcd_api_key)
            )
        else:
            logger.info("Initializing local Weaviate client")
            self.client = weaviate.connect_to_local()

        # Verify connection
        self.client.is_ready()
        return self.client

    def create(self) -> None:
        """Create the collection in Weaviate if it doesn't exist."""
        if not self.exists():
            logger.debug(f"Creating collection '{self.collection}' in Weaviate.")
            self.get_client().collections.create(
                name=self.collection,
                properties=[
                    Property(name="name", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="meta_data", data_type=DataType.TEXT),
                ],
                vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(
                    ef_construction=128,
                    max_connections=16,
                ),
            )
            logger.debug(f"Collection '{self.collection}' created in Weaviate.")

    def doc_exists(self, document: Document) -> bool:
        """
        Validate if the document exists using consistent UUID generation.

        Args:
            document (Document): Document to validate

        Returns:
            bool: True if the document exists, False otherwise
        """
        if not document or not document.content:
            logger.warning("Invalid document: Missing content.")
            return False  # Early exit for invalid input

        cleaned_content = document.content.replace("\x00", "\ufffd")
        content_hash = md5(cleaned_content.encode()).hexdigest()
        doc_uuid = uuid.UUID(hex=content_hash[:32])

        collection = self.get_client().collections.get(self.collection)
        return collection.data.exists(doc_uuid)

    def name_exists(self, name: str) -> bool:
        """
        Validate if a document with the given name exists in Weaviate.

        Args:
            name (str): The name of the document to check.

        Returns:
            bool: True if a document with the given name exists, False otherwise.
        """
        collection = self.get_client().collections.get(self.collection)
        result = collection.query.fetch_objects(
            limit=1,
            filters=Filter.by_property("name").equal(name),
        )
        return len(result.objects) > 0

    def insert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """
        Insert documents into Weaviate.

        Args:
            documents (List[Document]): List of documents to insert
            filters (Optional[Dict[str, Any]]): Filters to apply while inserting documents
        """
        logger.debug(f"Inserting {len(documents)} documents into Weaviate.")
        collection = self.get_client().collections.get(self.collection)

        for document in documents:
            document.embed(embedder=self.embedder)
            if document.embedding is None:
                logger.error(f"Document embedding is None: {document.name}")
                continue

            cleaned_content = document.content.replace("\x00", "\ufffd")
            content_hash = md5(cleaned_content.encode()).hexdigest()
            doc_uuid = uuid.UUID(hex=content_hash[:32])

            # Serialize meta_data to JSON string
            meta_data_str = json.dumps(document.meta_data) if document.meta_data else None

            collection.data.insert(
                properties={
                    "name": document.name,
                    "content": cleaned_content,
                    "meta_data": meta_data_str,
                },
                vector=document.embedding,
                uuid=doc_uuid,
            )
            logger.debug(f"Inserted document: {document.name} ({document.meta_data})")

    def upsert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """
        Upsert documents into Weaviate.

        Args:
            documents (List[Document]): List of documents to upsert
            filters (Optional[Dict[str, Any]]): Filters to apply while upserting
        """
        logger.debug(f"Upserting {len(documents)} documents into Weaviate.")
        self.insert(documents)

    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Perform a search based on the configured search type.

        Args:
            query (str): The search query.
            limit (int): Maximum number of results to return.
            filters (Optional[Dict[str, Any]]): Filters to apply to the search.

        Returns:
            List[Document]: List of matching documents.
        """
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for query: {query}")
            return []

        if self.search_type == SearchType.vector:
            return self.vector_search(query_embedding, limit)
        elif self.search_type == SearchType.keyword:
            return self.keyword_search(query, limit)
        elif self.search_type == SearchType.hybrid:
            return self.hybrid_search(query_embedding, query, limit)
        else:
            logger.error(f"Invalid search type '{self.search_type}'.")
            return []

    def vector_search(self, query_embedding: List[float], limit: int = 5) -> List[Document]:
        """
        Perform a vector search in Weaviate.

        Args:
            query_embedding (List[float]): The vector of the query to search.
            limit (int): Maximum number of results to return.

        Returns:
            List[Document]: List of matching documents.
        """
        collection = self.get_client().collections.get(self.collection)
        response = collection.query.near_vector(
            near_vector=query_embedding,
            limit=limit,
            return_properties=["name", "content", "meta_data"],
            include_vector=True,
        )

        search_results: List[Document] = []
        for obj in response.objects:
            properties = obj.properties
            meta_data = json.loads(properties["meta_data"]) if properties.get("meta_data") else None
            # Extract vector from default key
            embedding = obj.vector["default"] if isinstance(obj.vector, dict) else obj.vector

            search_results.append(
                Document(
                    name=properties["name"],
                    meta_data=meta_data,
                    content=properties["content"],
                    embedder=self.embedder,
                    embedding=embedding,  # Now passing list instead of dict
                    usage=None,
                )
            )

        if self.reranker:
            search_results = self.reranker.rerank(query=query_embedding, documents=search_results)

        self.get_client().close()
        return search_results

    def keyword_search(self, query: str, limit: int = 5) -> List[Document]:
        """
        Perform a keyword search in Weaviate.

        Args:
            query (str): The search query.
            limit (int): Maximum number of results to return.

        Returns:
            List[Document]: List of matching documents.
        """
        collection = self.get_client().collections.get(self.collection)
        response = collection.query.bm25(
            query=query,
            query_properties=["content"],
            limit=limit,
            return_properties=["name", "content", "meta_data"],
            include_vector=True,
        )

        search_results: List[Document] = []
        for obj in response.objects:
            properties = obj.properties
            meta_data = json.loads(properties["meta_data"]) if properties.get("meta_data") else None
            embedding = obj.vector["default"] if isinstance(obj.vector, dict) else obj.vector

            search_results.append(
                Document(
                    name=properties["name"],
                    meta_data=meta_data,
                    content=properties["content"],
                    embedder=self.embedder,
                    embedding=embedding,
                    usage=None,
                )
            )

        self.get_client().close()
        return search_results

    def hybrid_search(self, query_embedding: List[float], query: str, limit: int = 5) -> List[Document]:
        """
        Perform a hybrid search combining vector and keyword search in Weaviate.

        Args:
            query_embedding (List[float]): The vector of the query to search.
            query (str): The keyword query.
            limit (int): Maximum number of results to return.

        Returns:
            List[Document]: List of matching documents.
        """
        collection = self.get_client().collections.get(self.collection)
        response = collection.query.hybrid(
            query=query,
            vector=query_embedding,
            limit=limit,
            return_properties=["name", "content", "meta_data"],
            include_vector=True,
        )

        search_results: List[Document] = []
        for obj in response.objects:
            properties = obj.properties
            meta_data = json.loads(properties["meta_data"]) if properties.get("meta_data") else None
            embedding = obj.vector["default"] if isinstance(obj.vector, dict) else obj.vector

            search_results.append(
                Document(
                    name=properties["name"],
                    meta_data=meta_data,
                    content=properties["content"],
                    embedder=self.embedder,
                    embedding=embedding,
                    usage=None,
                )
            )

        if self.reranker:
            search_results = self.reranker.rerank(query=query, documents=search_results)

        self.get_client().close()
        return search_results

    def exists(self) -> bool:
        """Check if the collection exists in Weaviate."""
        return self.get_client().collections.exists(self.collection)

    def get_count(self) -> int:
        """Get the number of documents in the Weaviate collection."""
        collection = self.get_client().collections.get(self.collection)
        return collection.aggregate.over_all(total_count=True).total_count

    def drop(self) -> None:
        """Delete the Weaviate collection."""
        if self.exists():
            logger.debug(f"Deleting collection '{self.collection}' from Weaviate.")
            self.get_client().collections.delete(self.collection)

    def optimize(self) -> None:
        """Optimize the vector database (e.g., rebuild indexes)."""
        pass

    def delete(self) -> bool:
        """Delete all records from the database."""
        collection = self.get_client().collections.get(self.collection)
        collection.data.delete_all()
        return True
