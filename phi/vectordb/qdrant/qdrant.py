from typing import Optional, List, Union
from hashlib import md5

try:
    from qdrant_client import QdrantClient  # noqa: F401
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

    def create(self) -> None:
        pass

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        pass

    def insert(self, documents: List[Document], batch_size: int = 10) -> None:
        pass

    def upsert(self, documents: List[Document]) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
        """
        pass

    def search(self, query: str, limit: int = 5) -> List[Document]:
        pass

    def delete(self) -> None:
        pass

    def exists(self) -> bool:
        pass

    def get_count(self) -> int:
        pass

    def optimize(self) -> None:
        pass
