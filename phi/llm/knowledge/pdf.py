from pathlib import Path
from typing import Union, List, Optional, Iterator

from phi.document import Document
from phi.document.reader.pdf import PDFReader
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.llm.knowledge.base import KnowledgeBase
from phi.vectordb import VectorDb
from phi.utils.log import logger


class PDFKnowledgeBase(KnowledgeBase):
    """Model for managing a PDF knowledge base"""

    # Provide a path to a directory of PDFs
    path: Optional[Union[str, Path]] = None
    # Provide a PDF reader to read the PDFs
    reader: PDFReader = PDFReader()
    # Provide an embedder to embed the PDFs and search queries
    embedder: Embedder = OpenAIEmbedder()
    # Provide a vector db to store and search the knowledge base
    vector_db: Optional[VectorDb] = None

    @property
    def documents(self) -> Iterator[Document]:
        """Return all documents in the knowledge base"""

        kb_path = Path(self.path) if isinstance(self.path, str) else self.path
        if kb_path is not None:
            if kb_path.exists() and kb_path.is_dir():
                for _pdf in kb_path.glob("*.pdf"):
                    yield from self.reader.read(path=_pdf)
            elif kb_path.exists() and kb_path.is_file() and kb_path.suffix == ".pdf":
                yield from self.reader.read(path=kb_path)

    def search(self, query: str, num_documents: int = 5) -> List[Document]:
        """Return all relevant documents matching the query"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return []

        logger.info(f"Getting relevant documents for query: {query}")
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for question: {query}")
            return []

        return self.vector_db.search(query_embedding=query_embedding, num_documents=num_documents)

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
        for document in self.documents:
            document.embed(embedder=self.embedder)
            self.vector_db.insert(document=document)
            logger.info(f"Inserted document: {document.name} ({document.meta_data})")
            num_documents += 1
        logger.info(f"Loaded {num_documents} documents to knowledge base")
