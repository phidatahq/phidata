from hashlib import md5
from typing import List, Optional
from collections import defaultdict

try:
    import chromadb
except ImportError:
    raise ImportError("The `chromadb` package is not installed. " "Please install it via `pip install chromadb`.")

from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance
from phi.utils.log import logger


class ChromaDb(VectorDb):
    def __init__(
        self,
        collection: str,
        embedder: Embedder = OpenAIEmbedder(),
        distance: Distance = Distance.cosine,
        port: Optional[int] = 8000,
        **kwargs,
    ):
        # Collection attributes
        self.collection: str = collection

        # Embedder for embedding the document contents
        self.embedder: Embedder = embedder
        self.dimensions: int = self.embedder.dimensions

        # Distance metric
        self.distance: Distance = distance

        # Chromadb client instance
        self._client: Optional[chromadb.HttpClient] = None

        # Chromadb client arguments
        self.port: Optional[int] = port

        # Chromadb client kwargs
        self.kwargs = kwargs

    @property
    def client(self) -> chromadb.HttpClient():
        if self._client is None:
            logger.debug("Creating Chromadb Client")
            self._client = chromadb.HttpClient(
                port=self.port,
                **self.kwargs,
            )
        return self._client

    def create(self) -> None:
        logger.debug(f"Creating collection: {self.collection}")
        self.collection_name = self.client.create_collection(
            name=self.collection, embedding_function=self.openai_ef, metadata={"hnsw:space": "cosine"}
        )

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        # if self.client:
        #     cleaned_content = document.content.replace("\x00", "\uFFFD")
        #     doc_id = md5(cleaned_content.encode()).hexdigest()
        #     collection_points = self.client.get(
        #         collection_name=self.collection,
        #         ids=[doc_id],
        #     )
        #     return len(collection_points) > 0
        return False

    def name_exists(self, name: str) -> bool:
        raise NotImplementedError

    def insert(self, documents: List[Document], batch_size: int = 10) -> None:
        logger.debug(f"Inserting {len(documents)} documents")

        content = defaultdict(list)
        for document in documents:
            document.embed(embedder=self.openai_ef)
            cleaned_content = document.content.replace("\x00", "\uFFFD")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            content["ids"].append(doc_id)
            content["content"].append(cleaned_content)
            logger.debug(f"Inserted document: {document.name} ({document.meta_data})")
        if len(content) > 0:
            self.collection_name.add(documents=content["content"], ids=content["ids"])
        logger.debug(f"Upsert {len(content)} documents")

    def upsert(self, documents: List[Document]) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
        """
        # logger.debug("Redirecting the request to insert")
        # self.insert(documents)

        return False

    def search(self, query: str, limit: int = 5) -> List[Document]:
        # query_embedding = self.embedder.get_embedding(query)
        # if query_embedding is None:
        #     logger.error(f"Error getting embedding for Query: {query}")
        #     return []

        # results = self.client.search(
        #     collection_name=self.collection,
        #     query_vector=query_embedding,
        #     with_vectors=True,
        #     with_payload=True,
        #     limit=limit,
        # )

        # # Build search results
        # search_results: List[Document] = []
        # for result in results:
        #     if result.payload is None:
        #         continue
        #     search_results.append(
        #         Document(
        #             name=result.payload["name"],
        #             meta_data=result.payload["meta_data"],
        #             content=result.payload["content"],
        #             embedder=self.embedder,
        #             embedding=result.vector,
        #             usage=result.payload["usage"],
        #         )
        #     )

        # return search_results

        return None

    def delete(self) -> None:
        # if self.exists():
        #     logger.debug(f"Deleting collection: {self.collection}")
        #     self.client.delete_collection(self.collection)

        return None

    def exists(self) -> bool:
        # if self.client:
        #     collections_response: models.CollectionsResponse = self.client.get_collections()
        #     collections: List[models.CollectionDescription] = collections_response.collections
        #     for collection in collections:
        #         if collection.name == self.collection:
        #             # collection.status == models.CollectionStatus.GREEN
        #             return True
        return False

    def get_count(self) -> int:
        # count_result: models.CountResult = self.client.count(collection_name=self.collection, exact=True)
        # return count_result.count
        pass

    def optimize(self) -> None:
        pass
