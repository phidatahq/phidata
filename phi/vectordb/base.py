from abc import ABC, abstractmethod
from typing import List, Optional

from phi.document import Document


class VectorDB(ABC):
    @abstractmethod
    def create(self):
        raise NotImplementedError

    @abstractmethod
    def insert(self, document: Document):
        raise NotImplementedError

    @abstractmethod
    def search(self, embeddings: List[float]) -> Optional[List[Document]]:
        raise NotImplementedError
