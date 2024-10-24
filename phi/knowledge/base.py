from typing import List, Optional, Iterator, Dict, Any
from pydantic import BaseModel, ConfigDict
from phi.document import Document
from phi.document.reader.base import Reader
from phi.vectordb import VectorDb
from phi.utils.log import logger

class AssistantKnowledge(BaseModel):
    """Base class for managing an Assistant's knowledge base."""

    reader: Optional[Reader] = None  # Reader to read the documents
    vector_db: Optional[VectorDb] = None  # Vector database to store the knowledge base
    num_documents: int = 2  # Number of relevant documents to return on search
    optimize_on: Optional[int] = 1000  # Number of documents to optimize the vector db on

    driver: str = "knowledge"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterator that yields lists of documents in the knowledge base."""
        raise NotImplementedError("Subclasses must implement document_lists.")

    def search(self, query: str, num_documents: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Search for relevant documents matching a query.

        Args:
            query (str): The search query.
            num_documents (Optional[int]): Number of documents to return. Defaults to the class attribute.
            filters (Optional[Dict[str, Any]]): Filters to apply to the search.

        Returns:
            List[Document]: A list of relevant documents.
        """
        if self.vector_db is None:
            logger.warning("No vector db provided.")
            return []

        num_documents = num_documents or self.num_documents
        logger.debug(f"Searching for {_num_documents} relevant documents for query: '{query}'")
        
        try:
            return self.vector_db.search(query=query, limit=num_documents, filters=filters)
        except Exception as e:
            logger.error(f"Error searching for documents: {e}")
            return []

    def load(self, recreate: bool = False, upsert: bool = False, skip_existing: bool = True, filters: Optional[Dict[str, Any]] = None) -> None:
        """Load the knowledge base into the vector db.

        Args:
            recreate (bool): If True, recreate the collection in the vector db.
            upsert (bool): If True, upsert documents to the vector db.
            skip_existing (bool): If True, skip documents that already exist in the vector db.
            filters (Optional[Dict[str, Any]]): Filters to apply when loading documents.
        """
        if self.vector_db is None:
            logger.warning("No vector db provided.")
            return

        if recreate:
            logger.info("Dropping existing collection.")
            self.vector_db.drop()

        logger.info("Creating new collection.")
        self.vector_db.create()

        logger.info("Loading knowledge base.")
        total_documents_loaded = 0
        for document_list in self.document_lists:
            documents_to_load = self._prepare_documents_to_load(document_list, upsert, skip_existing, filters)
            if documents_to_load:
                self.vector_db.insert(documents=documents_to_load, filters=filters)
                total_documents_loaded += len(documents_to_load)
                logger.info(f"Added {len(documents_to_load)} documents to knowledge base.")

        logger.info(f"Total documents loaded: {total_documents_loaded}")

    def _prepare_documents_to_load(self, document_list: List[Document], upsert: bool, skip_existing: bool, filters: Optional[Dict[str, Any]]) -> List[Document]:
        """Prepare documents for loading, filtering out existing ones if required.

        Args:
            document_list (List[Document]): List of documents to load.
            upsert (bool): If True, upserts documents if they exist.
            skip_existing (bool): If True, skips documents that already exist.
            filters (Optional[Dict[str, Any]]): Filters to apply when loading documents.

        Returns:
            List[Document]: List of documents ready for loading.
        """
        if upsert and self.vector_db.upsert_available():
            self.vector_db.upsert(documents=document_list, filters=filters)
            return []

        if skip_existing:
            return [doc for doc in document_list if not self.vector_db.doc_exists(doc)]
        return document_list

    def load_documents(self, documents: List[Document], upsert: bool = False, skip_existing: bool = True, filters: Optional[Dict[str, Any]] = None) -> None:
        """Load a list of documents into the knowledge base.

        Args:
            documents (List[Document]): List of documents to load.
            upsert (bool): If True, upserts documents if they exist.
            skip_existing (bool): If True, skips documents that already exist.
            filters (Optional[Dict[str, Any]]): Filters to apply when loading documents.
        """
        if self.vector_db is None:
            logger.warning("No vector db provided.")
            return

        logger.info("Loading documents into knowledge base.")
        self.vector_db.create()  # Create collection if it doesn't exist

        documents_to_load = self._prepare_documents_to_load(documents, upsert, skip_existing, filters)
        if documents_to_load:
            self.vector_db.insert(documents=documents_to_load, filters=filters)
            logger.info(f"Loaded {len(documents_to_load)} documents into knowledge base.")
        else:
            logger.info("No new documents to load.")

    def exists(self) -> bool:
        """Check if the knowledge base exists.

        Returns:
            bool: True if the knowledge base exists, False otherwise.
        """
        if self.vector_db is None:
            logger.warning("No vector db provided.")
            return False
        return self.vector_db.exists()

    def delete(self) -> bool:
        """Clear the knowledge base.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        if self.vector_db is None:
            logger.warning("No vector db available.")
            return True

        return self.vector_db.delete()
