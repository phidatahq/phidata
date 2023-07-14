from pathlib import Path
from typing import Union, List, Optional

from pydantic import BaseModel

from phi.document import Document
from phi.document.pdf import PDF
from phi.llm.knowledge.base import KnowledgeBase
from phi.vectordb import VectorDB


class PDFKnowledgeBase(BaseModel, KnowledgeBase):
    """Model for managing a PDF knowledge base"""

    name: Optional[str] = None
    path: Optional[Union[str, Path]] = None
    pdfs: List[PDF] = []
    vector_db: Optional[VectorDB] = None

    def get_all_documents(self) -> List[Document]:
        """Return all documents in the knowledge base"""
        raise NotImplementedError

    def get_relevant_documents(self, query: str) -> List[Document]:
        """Return all relevant documents matching the query"""
        raise NotImplementedError

    def load_knowledge_base(self) -> bool:
        """Load the knowledge base to vector db"""
        raise NotImplementedError
