from abc import ABC, abstractmethod
from typing import List, Iterator

from phi.document import Document


class KnowledgeBase(ABC):
    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over document lists in the knowledge base"""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str) -> List[Document]:
        """Return all relevant documents matching the query"""
        raise NotImplementedError

    @abstractmethod
    def load_knowledge_base(self, recreate: bool = False) -> None:
        """Load the knowledge base to vector db"""
        raise NotImplementedError
