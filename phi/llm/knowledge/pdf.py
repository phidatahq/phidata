from pathlib import Path
from typing import Union, List, Optional, Iterator

from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.llm.knowledge.base import LLMKnowledgeBase
from phi.vectordb import VectorDb
from phi.utils.log import logger


class PDFKnowledgeBase(LLMKnowledgeBase):
    path: Union[str, Path]
    reader: PDFReader = PDFReader()
    vector_db: Optional[VectorDb] = None
    relevant_documents: int = 5

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDFs and return a list of document in each PDF
        Returns:
            Iterator[List[Document]]: Iterator over List of documents in each PDF
        """

        pdf_dir_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if pdf_dir_path.exists() and pdf_dir_path.is_dir():
            for _pdf in pdf_dir_path.glob("*.pdf"):
                yield self.reader.read(path=_pdf)
        elif pdf_dir_path.exists() and pdf_dir_path.is_file() and pdf_dir_path.suffix == ".pdf":
            yield self.reader.read(path=pdf_dir_path)

    def search(self, query: str, num_documents: Optional[int] = None) -> List[Document]:
        """Return all relevant documents matching the query"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return []

        _num_documents = num_documents or self.relevant_documents
        logger.debug(f"Getting {_num_documents} relevant documents for query: {query}")
        return self.vector_db.search(query=query, num_documents=_num_documents)

    def load(self, recreate: bool = False) -> None:
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
