from typing import List, Optional, Dict
from hashlib import md5

try:
    import chromadb
except ImportError:
    raise ImportError("The `chromadb` package is not installed, please install using `pip install chromadb`.")

from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.utils.log import logger


class ChromaDB(VectorDb):
    def __init__(
        self,
        collection: str,
        embedder: Embedder = OpenAIEmbedder(),
        namespace: Optional[str] = "",
        hostname: Optional[str] = "localhost",
        port: Optional[int] = 8000,
        headers: Optional[Dict[str, str]] = None,
        ssl: Optional[bool] = False,
    ):
        self.collection = collection
        self.embedder = embedder
        self.namespace = namespace
        self.hostname = hostname
        self.port = port
        self.headers = headers
        self.ssl = ssl
        self._client = chromadb.Client()

        # Create the collection if it does not exist
        self.create()

    def create(self) -> None:
        """
        Create a new collection in ChromaDB
        """
        logger.debug(f"Creating collection {self.collection}")
        self._client.create_collection(self.collection)

    def doc_exists(self, document: Document) -> bool:
        """
        Check if a document exists in the collection by computing the MD5 hash of its text
        and querying the database for this hash.

        Parameters:
        - document (Document): The document object with a 'text' attribute.

        Returns:
        - bool: True if the document exists in the collection, False otherwise.
        """
        if self._client:
            collection = self._client.get_collection(self.collection)
            cleaned_text = document.content.replace("\x00", "\ufffd").strip()
            doc_id = md5(cleaned_text.encode()).hexdigest()
            collection_points = collection.query(
                where={"ids": doc_id},
            )
            return len(collection_points) > 0
        return False

    def insert(self, documents: List[Document]) -> None:
        """
        Insert documents into the collection
        """
        if self._client:
            logger.debug(f"Inserting {len(documents)} documents")
            collection = self._client.get_collection(self.collection)

            # Data to be inserted
            col_documents = []
            col_ids = []

            for document in documents:
                document.embed(embedder=self.embedder)
                cleaned_text = document.content.replace("\x00", "\ufffd")
                doc_id = str(md5(cleaned_text.encode()).hexdigest())

                col_documents.append(cleaned_text)
                col_ids.append(doc_id)
                logger.debug(f"Inserted document: {document.name} ({document.meta_data})")

            # Insert the documents
            collection.add(
                documents=col_documents,
                ids=col_ids,
            )
            logger.debug(f"Upsert {len(col_documents)} documents")

    def upsert(self, documents: List[Document]) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
        """
        logger.debug("Redirecting the request to insert")
        self.insert(documents)

    def search(self, query: str, limit: int = 5) -> List[Document]:
        raise NotImplementedError

    def name_exists(self, name: str) -> bool:
        raise NotImplementedError

    def delete(self) -> None:
        """
        Delete the collection from ChromaDB
        """
        if self.exists():
            logger.debug(f"Deleting collection {self.collection}")
            return self._client.delete_collection(name=self.collection)

    def exists(self) -> bool:
        """
        Check if the collection exists in ChromaDB
        """
        if self._client:
            # List all collections and check if the collection exists
            for collection in self._client.list_collections():
                if collection.name == self.collection:
                    return True
        return False

    def get_count(self) -> int:
        """
        Get the number of documents in the collection
        """
        chromadb_collection = self._client.get_collection(self.collection)
        if chromadb_collection is not None:
            return chromadb_collection.count()
        return 0

    def optimize(self) -> None:
        raise NotImplementedError

    def clear(self) -> bool:
        raise NotImplementedError
