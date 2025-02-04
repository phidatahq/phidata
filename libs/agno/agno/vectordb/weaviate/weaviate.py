from hashlib import md5
from typing import List, Optional, Dict, Any
import json
import uuid

import weaviate
from weaviate.classes.config import Property, DataType, Configure
from weaviate.classes.query import Filter
from phi.document import Document
from phi.embedder import Embedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance
from phi.vectordb.search import SearchType
from phi.utils.log import logger
from phi.reranker.base import Reranker


class Weaviate(VectorDb):
    """
    Weaviate class for managing vector operations with Weaviate vector database (v4 client).
    """

    def __init__(
        self,
        client: Optional[weaviate.WeaviateClient] = None,
        index_name: str = "default",
        embedder: Optional[Embedder] = None,
        search_type: SearchType = SearchType.vector,
        distance: Distance = Distance.cosine,
        reranker: Optional[Reranker] = None,
    ):
        """
        Initialize the Weaviate instance.

        Args:
            client (weaviate.WeaviateClient): The Weaviate client instance.
            index_name (str): The name of the Weaviate collection (class).
            embedder (Optional[Embedder]): Embedder instance for creating embeddings.
            search_type (SearchType): Type of search to perform.
            distance (Distance): Distance metric for vector comparisons.
            reranker (Optional[Reranker]): Reranker instance for search results.
        """
        self._client = client
        self.index_name = index_name

        # Embedder for embedding the document contents
        if embedder is None:
            from phi.embedder.openai import OpenAIEmbedder

            embedder = OpenAIEmbedder()
        self.embedder: Embedder = embedder
        self.dimensions: Optional[int] = self.embedder.dimensions

        if self.dimensions is None:
            raise ValueError("Embedder.dimensions must be set.")

        # Search type
        self.search_type: SearchType = search_type
        # Distance metric
        self.distance: Distance = distance

        # Reranker instance
        self.reranker: Optional[Reranker] = reranker

        logger.debug(f"Initialized Weaviate with collection: '{self.index_name}'")

    @property
    def client(self) -> weaviate.WeaviateClient:
        """The Weaviate client.

        Returns:
            weaviate.WeaviateClient: The Weaviate client.
        """
        if self._client is None:
            logger.debug("Creating Weaviate Client")
            self._client = weaviate.connect_to_local()
        return self._client

    def create(self) -> None:
        """Create the collection in Weaviate if it doesn't exist."""
        if not self.exists():
            logger.debug(f"Creating collection '{self.index_name}' in Weaviate.")
            self.client.collections.create(
                name=self.index_name,
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
            logger.debug(f"Collection '{self.index_name}' created in Weaviate.")

    def doc_exists(self, document: Document) -> bool:
        """
        Validate if the document exists using consistent UUID generation.

        Args:
            document (Document): Document to validate

        Returns:
            bool: True if the document exists, False otherwise
        """
        # Generate UUID from document name (consistent with insert)
        key_properties = {"name": document.name}
        key_str = json.dumps(key_properties, sort_keys=True)
        weaviate_namespace = uuid.UUID("7e12415e-8e90-4522-b165-74c72a28cb2b")
        doc_uuid = uuid.uuid5(weaviate_namespace, key_str)

        collection = self.client.collections.get(self.index_name)
        return collection.data.exists(doc_uuid)

    def name_exists(self, name: str) -> bool:
        """
        Validate if a document with the given name exists in Weaviate.

        Args:
            name (str): The name of the document to check.

        Returns:
            bool: True if a document with the given name exists, False otherwise.
        """
        collection = self.client.collections.get(self.index_name)
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
        collection = self.client.collections.get(self.index_name)

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
        collection = self.client.collections.get(self.index_name)
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
        collection = self.client.collections.get(self.index_name)
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
        collection = self.client.collections.get(self.index_name)
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

        return search_results

    def exists(self) -> bool:
        """Check if the collection exists in Weaviate."""
        return self.client.collections.exists(self.index_name)

    def get_count(self) -> int:
        """Get the number of documents in the Weaviate collection."""
        collection = self.client.collections.get(self.index_name)
        return collection.aggregate.over_all(total_count=True).total_count

    def drop(self) -> None:
        """Delete the Weaviate collection."""
        if self.exists():
            logger.debug(f"Deleting collection '{self.index_name}' from Weaviate.")
            self.client.collections.delete(self.index_name)

    def optimize(self) -> None:
        """Optimize the vector database (e.g., rebuild indexes)."""
        pass

    def delete(self) -> bool:
        """Delete all records from the database."""
        collection = self.client.collections.get(self.index_name)
        collection.data.delete_all()
        return True
