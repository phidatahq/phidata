from pathlib import Path
from typing import Union, List, Optional, Iterator

from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.llm.knowledge.base import KnowledgeBase
from phi.vectordb import VectorDb
from phi.utils.log import logger


class PDFKnowledgeBase(KnowledgeBase):
    def __init__(
        self, path: Union[str, Path], reader: Optional[PDFReader] = None, vector_db: Optional[VectorDb] = None
    ):
        if not (isinstance(path, str) or isinstance(path, Path)):
            raise TypeError(f"Path must be of type str or Path, got: {type(path)}")

        self.path: Path = Path(path) if isinstance(path, str) else path
        self.reader: PDFReader = reader or PDFReader()
        self.vector_db: Optional[VectorDb] = vector_db

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDFs and return a list of document in each PDF
        Returns:
            Iterator[List[Document]]: Iterator over List of documents in each PDF
        """

        if self.path.exists() and self.path.is_dir():
            for _pdf in self.path.glob("*.pdf"):
                yield self.reader.read(path=_pdf)
        elif self.path.exists() and self.path.is_file() and self.path.suffix == ".pdf":
            yield self.reader.read(path=self.path)

    def search(self, query: str, num_documents: int = 5) -> List[Document]:
        """Return all relevant documents matching the query"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return []

        logger.debug(f"Getting relevant documents for query: {query}")
        return self.vector_db.search(query=query, num_documents=num_documents)

    def load_knowledge_base(self, recreate: bool = False) -> None:
        """Load the knowledge base to vector db"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        if recreate:
            logger.debug("Recreating collection")
            self.vector_db.delete()

        logger.debug("Creating collection")
        self.vector_db.create()

        logger.info("Loading knowledge base")
        num_documents = 0
        for document_list in self.document_lists:
            self.vector_db.insert(documents=document_list)
            logger.debug(f"Inserted {len(document_list)} documents")
            num_documents += len(document_list)
        logger.info(f"Loaded {num_documents} documents to knowledge base")
