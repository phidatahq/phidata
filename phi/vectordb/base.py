from abc import ABC, abstractmethod
from typing import List

from phi.document import Document


class VectorDB(ABC):
    @abstractmethod
    def create(self):
        raise NotImplementedError

    @abstractmethod
    def upsert(self, documents: List[Document]):
        raise NotImplementedError
