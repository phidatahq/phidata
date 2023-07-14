from abc import ABC, abstractmethod

from phi.document import Document


class VectorDB(ABC):
    @abstractmethod
    def create(self):
        raise NotImplementedError

    @abstractmethod
    def insert(self, document: Document):
        raise NotImplementedError
