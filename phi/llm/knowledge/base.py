from abc import ABC, abstractmethod
from typing import List

from phi.document import Document


class KnowledgeBase(ABC):
    """Base class for managing knowledge base"""

    @abstractmethod
    def get_all_documents(self) -> List[Document]:
        """Return all documents in the knowledge base"""
        raise NotImplementedError

    @abstractmethod
    def get_relevant_documents(self, query: str) -> List[Document]:
        """Return all relevant documents matching the query"""
        raise NotImplementedError

    @abstractmethod
    def load_knowledge_base(self) -> bool:
        """Load the knowledge base to vector db"""
        raise NotImplementedError
