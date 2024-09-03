from hashlib import md5
from typing import List, Optional

try:
    from chromadb import Client as ChromaDbClient
    from chromadb import PersistentClient as PersistentChromaDbClient
    from chromadb.api.client import ClientAPI
    from chromadb.api.models.Collection import Collection
    from chromadb.api.types import QueryResult, GetResult

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
        path: str = "tmp/chromadb",
        persistent_client: bool = False,
        **kwargs,
    ):
        # Collection attributes
        self.collection: str = collection

        # Embedder for embedding the document contents
        self.embedder: Embedder = embedder

        # Distance metric
        self.distance: Distance = distance

        # Chroma client instance
        self._client: Optional[ClientAPI] = None

        # Chroma collection instance
        self._collection: Optional[Collection] = None

        # Persistent Chroma client instance
        self.persistent_client: bool = persistent_client
        self.path: str = path

        # Chroma client kwargs
        self.kwargs = kwargs

    @property
    def client(self) -> ClientAPI:
        if self._client is None:
            if not self.persistent_client:
                logger.debug("Creating Chroma Client")
                self._client = ChromaDbClient(
                    **self.kwargs,
                )
            elif self.persistent_client:
                logger.debug("Creating Persistent Chroma Client")
                self._client = PersistentChromaDbClient(
                    path=self.path,
                    **self.kwargs,
                )
        return self._client

    def create(self) -> None:
        """Create the collection in ChromaDb."""
        if not self.exists():
            logger.debug(f"Creating collection: {self.collection}")
            self._collection = self.client.create_collection(
                name=self.collection, metadata={"hnsw:space": self.distance.value}
            )

    def doc_exists(self, document: Document) -> bool:
        """Check if a document exists in the collection.
        Args:
            document (Document): Document to check.
        Returns:
            bool: True if document exists, False otherwise.
        """
        if self.client:
            try:
                collection: Collection = self.client.get_collection(name=self.collection)
                collection_data: GetResult = collection.get(include=["documents"])
                if collection_data.get("documents") != []:
                    return True
            except Exception as e:
                logger.error(f"Document does not exist: {e}")
        return False

    def name_exists(self, name: str) -> bool:
        """Check if a document with a given name exists in the collection.
        Args:
            name (str): Name of the document to check.
        Returns:
            bool: True if document exists, False otherwise."""
        if self.client:
            try:
                collections: Collection = self.client.get_collection(name=self.collection)
                for collection in collections:
                    if name in collection:
                        return True
            except Exception as e:
                logger.error(f"Document with given name does not exist: {e}")
        return False

    def insert(self, documents: List[Document]) -> None:
        """Insert documents into the collection.
        Args:
            documents (List[Document]): List of documents to insert
        """
        logger.debug(f"Inserting {len(documents)} documents")
        ids: List = []
        docs: List = []
        docs_embeddings: List = []

        for document in documents:
            document.embed(embedder=self.embedder)
            cleaned_content = document.content.replace("\x00", "\ufffd")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            docs_embeddings.append(document.embedding)
            docs.append(cleaned_content)
            ids.append(doc_id)

        if len(docs) > 0 and self._collection is not None:
            self._collection.add(ids=ids, embeddings=docs_embeddings, documents=docs)
            logger.debug(f"Inserted {len(docs)} documents")
        else:
            logger.error("Collection does not exist")

    def upsert(self, documents: List[Document]) -> None:
        """Upsert documents into the collection.
        Args:
            documents (List[Document]): List of documents to upsert
        """
        logger.debug(f"Inserting {len(documents)} documents")
        ids: List = []
        docs: List = []
        docs_embeddings: List = []

        for document in documents:
            document.embed(embedder=self.embedder)
            cleaned_content = document.content.replace("\x00", "\ufffd")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            docs_embeddings.append(document.embedding)
            docs.append(cleaned_content)
            ids.append(doc_id)

        if len(docs) > 0 and self._collection is not None:
            self._collection.upsert(ids=ids, embeddings=docs_embeddings, documents=docs)
            logger.debug(f"Inserted {len(docs)} documents")
        else:
            logger.error("Collection does not exist")

    def search(self, query: str, limit: int = 5) -> List[Document]:
        """Search the collection for a query.
        Args:
            query (str): Query to search for.
            limit (int): Number of results to return.
        Returns:
            List[Document]: List of search results.
        """
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        if not self._collection:
            self._collection = self.client.get_collection(name=self.collection)

        result: QueryResult = self._collection.query(
            query_embeddings=query_embedding,
            n_results=limit,
        )

        # Build search results
        search_results: List[Document] = []

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]  # type: ignore
        metadatas = result.get("metadatas", [[]])[0]  # type: ignore
        documents = result.get("documents", [[]])[0]  # type: ignore
        embeddings = result.get("embeddings")
        uris = result.get("uris")
        data = result.get("data")

        try:
            # Use zip to iterate over multiple lists simultaneously
            for id_, distance, metadata, document in zip(ids, distances, metadatas, documents):
                search_results.append(
                    Document(
                        id=id_,
                        distances=distance,
                        metadatas=metadata,
                        content=document,
                        embeddings=embeddings,
                        uris=uris,
                        data=data,
                    )
                )
        except Exception as e:
            logger.error(f"Error building search results: {e}")

        return search_results

    def delete(self) -> None:
        """Delete the collection."""
        if self.exists():
            logger.debug(f"Deleting collection: {self.collection}")
            self.client.delete_collection(name=self.collection)

    def exists(self) -> bool:
        """Check if the collection exists."""
        try:
            self.client.get_collection(name=self.collection)
            return True
        except Exception as e:
            logger.debug(f"Collection does not exist: {e}")
        return False

    def get_count(self) -> int:
        """Get the count of documents in the collection."""
        if self.exists():
            try:
                collection: Collection = self.client.get_collection(name=self.collection)
                return collection.count()
            except Exception as e:
                logger.error(f"Error getting count: {e}")
        return 0

    def optimize(self) -> None:
        pass

    def clear(self) -> bool:
        return False
