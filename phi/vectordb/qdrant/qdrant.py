from hashlib import md5
from typing import List, Optional

try:
    from qdrant_client import QdrantClient  # noqa: F401
    from qdrant_client.http import models
except ImportError:
    raise ImportError(
        "The `qdrant-client` package is not installed. " "Please install it via `pip install qdrant-client`."
    )

from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance
from phi.utils.log import logger


class Qdrant(VectorDb):
    def __init__(
        self,
        collection: str,
        embedder: Embedder = OpenAIEmbedder(),
        distance: Distance = Distance.cosine,
        location: Optional[str] = None,
        url: Optional[str] = None,
        port: Optional[int] = 6333,
        grpc_port: int = 6334,
        prefer_grpc: bool = False,
        https: Optional[bool] = None,
        api_key: Optional[str] = None,
        prefix: Optional[str] = None,
        timeout: Optional[float] = None,
        host: Optional[str] = None,
        path: Optional[str] = None,
        **kwargs,
    ):
        # Collection attributes
        self.collection: str = collection

        # Embedder for embedding the document contents
        self.embedder: Embedder = embedder
        self.dimensions: int = self.embedder.dimensions

        # Distance metric
        self.distance: Distance = distance

        # Qdrant client instance
        self._client: Optional[QdrantClient] = None

        # Qdrant client arguments
        self.location: Optional[str] = location
        self.url: Optional[str] = url
        self.port: Optional[int] = port
        self.grpc_port: int = grpc_port
        self.prefer_grpc: bool = prefer_grpc
        self.https: Optional[bool] = https
        self.api_key: Optional[str] = api_key
        self.prefix: Optional[str] = prefix
        self.timeout: Optional[float] = timeout
        self.host: Optional[str] = host
        self.path: Optional[str] = path

        # Qdrant client kwargs
        self.kwargs = kwargs

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            logger.debug("Creating Qdrant Client")
            self._client = QdrantClient(
                location=self.location,
                url=self.url,
                port=self.port,
                grpc_port=self.grpc_port,
                prefer_grpc=self.prefer_grpc,
                https=self.https,
                api_key=self.api_key,
                prefix=self.prefix,
                timeout=self.timeout,
                host=self.host,
                path=self.path,
                **self.kwargs,
            )
        return self._client

    def create(self) -> None:
        # Collection distance
        _distance = models.Distance.COSINE
        if self.distance == Distance.l2:
            _distance = models.Distance.EUCLID
        elif self.distance == Distance.max_inner_product:
            _distance = models.Distance.DOT

        if not self.exists():
            logger.debug(f"Creating collection: {self.collection}")
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=self.dimensions, distance=_distance),
            )

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        if self.client:
            cleaned_content = document.content.replace("\x00", "\ufffd")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            collection_points = self.client.retrieve(
                collection_name=self.collection,
                ids=[doc_id],
            )
            return len(collection_points) > 0
        return False

    def name_exists(self, name: str) -> bool:
        """
        Validates if a document with the given name exists in the collection.

        Args:
            name (str): The name of the document to check.

        Returns:
            bool: True if a document with the given name exists, False otherwise.
        """
        if self.client:
            scroll_result = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="name", match=models.MatchValue(value=name))]
                ),
                limit=1,
            )
            return len(scroll_result[0]) > 0
        return False

    def insert(self, documents: List[Document], batch_size: int = 10) -> None:
        logger.debug(f"Inserting {len(documents)} documents")
        points = []
        for document in documents:
            document.embed(embedder=self.embedder)
            cleaned_content = document.content.replace("\x00", "\ufffd")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            points.append(
                models.PointStruct(
                    id=doc_id,
                    vector=document.embedding,
                    payload={
                        "name": document.name,
                        "meta_data": document.meta_data,
                        "content": cleaned_content,
                        "usage": document.usage,
                    },
                )
            )
            logger.debug(f"Inserted document: {document.name} ({document.meta_data})")
        if len(points) > 0:
            self.client.upsert(collection_name=self.collection, wait=False, points=points)
        logger.debug(f"Upsert {len(points)} documents")

    def upsert(self, documents: List[Document]) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
        """
        logger.debug("Redirecting the request to insert")
        self.insert(documents)

    def search(self, query: str, limit: int = 5) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            with_vectors=True,
            with_payload=True,
            limit=limit,
        )

        # Build search results
        search_results: List[Document] = []
        for result in results:
            if result.payload is None:
                continue
            search_results.append(
                Document(
                    name=result.payload["name"],
                    meta_data=result.payload["meta_data"],
                    content=result.payload["content"],
                    embedder=self.embedder,
                    embedding=result.vector,
                    usage=result.payload["usage"],
                )
            )

        return search_results

    def delete(self) -> None:
        if self.exists():
            logger.debug(f"Deleting collection: {self.collection}")
            self.client.delete_collection(self.collection)

    def exists(self) -> bool:
        if self.client:
            collections_response: models.CollectionsResponse = self.client.get_collections()
            collections: List[models.CollectionDescription] = collections_response.collections
            for collection in collections:
                if collection.name == self.collection:
                    # collection.status == models.CollectionStatus.GREEN
                    return True
        return False

    def get_count(self) -> int:
        count_result: models.CountResult = self.client.count(collection_name=self.collection, exact=True)
        return count_result.count

    def optimize(self) -> None:
        pass

    def clear(self) -> bool:
        return False
