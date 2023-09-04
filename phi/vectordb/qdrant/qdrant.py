import os
from hashlib import md5
from typing import List

try:
    from qdrant_client import QdrantClient  # noqa: F401
    from qdrant_client.http import models
    from qdrant_client.http.models import CollectionStatus, PointStruct, UpdateResult, UpdateStatus
except ImportError:
    raise ImportError(
        "The `qdrant-client` package is not installed. "
        "Please install it via `pip install pip install qdrant-client`."
    )

from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import DistanceMetric
from phi.utils.log import logger


class Qdrant(VectorDb):
    def __init__(
        self,
        collection: str,
        embedder: Embedder = OpenAIEmbedder(),
        distance_metric: DistanceMetric = DistanceMetric.cosine,
    ):
        # Collection attributes
        self.collection: str = collection

        # Embedder for embedding the document contents
        self.embedder: Embedder = embedder
        self.dimensions: int = self.embedder.dimensions

        # Distance metric
        self.distance_metric: DistanceMetric = distance_metric

        # qdrant client
        self.client: QdrantClient = None
        # self.create()

    def create(self) -> None:
        logger.debug("Creating Qdrant Client")
        if not self.client:
            root_dir = os.path.abspath(os.curdir)
            self.client = QdrantClient(path=f"{root_dir}/.qdrant_db/", prefer_grpc=True)
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
            )

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        if self.client:
            cleaned_content = document.content.replace("\x00", "\uFFFD")
            collection_points = self.client.retrieve(
                collection_name=self.collection,
                ids=[cleaned_content],
            )
            return len(collection_points) > 0
        return False

    def name_exists(self, name: str) -> bool:
        print("********* NAME EXISTS **********")
        return True

    def insert(self, documents: List[Document], batch_size: int = 10) -> UpdateStatus:
        logger.debug(f"Inserting {len(documents)} documents")
        points = []
        for document in documents:
            document.embed(embedder=self.embedder)
            cleaned_content = document.content.replace("\x00", "\uFFFD")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            points.append(
                PointStruct(
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
        response: UpdateResult = self.client.upsert(collection_name=self.collection, wait=False, points=points)
        logger.debug(f"Upsert {len(points)} documents")
        return response.status

    def upsert(self, documents: List[Document]) -> UpdateStatus:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
        """
        logger.debug("Upserting, redirecting the request to insert")
        return self.insert(documents)

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
            collection_info = self.client.get_collection(collection_name=self.collection)
            return collection_info.status == CollectionStatus.GREEN

    def get_count(self) -> int:
        return self.client.count(collection_name=self.collection, exact=True)

    def optimize(self) -> None:
        pass
