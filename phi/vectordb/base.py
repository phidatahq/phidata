from abc import ABC, abstractmethod
from typing import List

from phi.document import Document


class VectorDb(ABC):
    """Base class for managing Vector Databases"""

    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def insert(self, documents: List[Document]) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, documents: List[Document]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, relevant_documents: int = 5) -> List[Document]:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError
