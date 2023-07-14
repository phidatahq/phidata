from pathlib import Path
from typing import Union, List, Optional, Iterator

from phi.document import Document
from phi.document.pdf import PDF
from phi.llm.knowledge.base import KnowledgeBase
from phi.vectordb import VectorDB
from phi.utils.log import logger


class PDFKnowledgeBase(KnowledgeBase):
    """Model for managing a PDF knowledge base"""

    path: Optional[Union[str, Path]] = None
    pdfs: List[PDF] = []
    vector_db: Optional[VectorDB] = None

    def get_documents(self) -> Iterator[Document]:
        """Return all documents in the knowledge base"""

        kb_path = Path(self.path) if isinstance(self.path, str) else self.path
        if kb_path is None:
            logger.warning("No knowledge base path provided")
            return

        if kb_path.exists() and kb_path.is_dir():
            for _pdf in kb_path.glob("*.pdf"):
                self.pdfs.append(PDF(path=_pdf))
        elif kb_path.exists() and kb_path.is_file() and kb_path.suffix == ".pdf":
            self.pdfs.append(PDF(path=kb_path))
        else:
            logger.warning(f"Invalid knowledge base path: {self.path}")

        logger.info(f"Found {len(self.pdfs)} PDFs in knowledge base")
        for pdf in self.pdfs:
            for document in pdf.read():
                yield document

    def search(self, query: str) -> List[Document]:
        """Return all relevant documents matching the query"""
        logger.info(f"Getting relevant documents for query: {query}")
        return []

    def load_knowledge_base(self) -> bool:
        """Load the knowledge base to vector db"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return False

        logger.info("Creating collection")
        self.vector_db.create()

        logger.info("Loading knowledge base")
        num_documents = 0
        for document in self.get_documents():
            document.embed()
            success = self.vector_db.insert(document=document)
            if success:
                num_documents += 1
        return True
