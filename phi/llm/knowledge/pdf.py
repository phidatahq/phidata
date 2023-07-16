from pathlib import Path
from typing import Union, List, Optional, Iterator

from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.llm.knowledge.base import KnowledgeBase
from phi.vectordb import VectorDb
from phi.utils.log import logger


class PDFKnowledgeBase(KnowledgeBase):
    """Model for managing a PDF knowledge base"""

    # Provide a path to a directory of PDFs
    path: Optional[Union[str, Path]] = None
    # Provide a PDF reader to read the PDFs
    reader: PDFReader = PDFReader()
    # Provide a vector db to store and search the knowledge base
    vector_db: Optional[VectorDb] = None

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDFs and return a list of document in each PDF
        Returns:
            Iterator[List[Document]]: Iterator over List of documents in each PDF
        """

        kb_path = Path(self.path) if isinstance(self.path, str) else self.path
        if kb_path is not None:
            if kb_path.exists() and kb_path.is_dir():
                for _pdf in kb_path.glob("*.pdf"):
                    yield self.reader.read(path=_pdf)
            elif kb_path.exists() and kb_path.is_file() and kb_path.suffix == ".pdf":
                yield self.reader.read(path=kb_path)

    def search(self, query: str, num_documents: int = 5) -> List[Document]:
        """Return all relevant documents matching the query"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return []

        logger.info(f"Getting relevant documents for query: {query}")
        return self.vector_db.search(query=query, num_documents=num_documents)

    def load_knowledge_base(self, recreate: bool = False) -> None:
        """Load the knowledge base to vector db"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        if recreate:
            logger.info("Recreating collection")
            self.vector_db.delete()

        logger.info("Creating collection")
        self.vector_db.create()

        logger.info("Loading knowledge base")
        num_documents = 0
        for document_list in self.document_lists:
            self.vector_db.insert(documents=document_list)
            logger.info(f"Inserted {len(document_list)} documents")
            num_documents += len(document_list)
        logger.info(f"Loaded {num_documents} documents to knowledge base")
