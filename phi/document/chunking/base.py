from abc import ABC, abstractmethod
from typing import List

from phi.document.base import Document


class ChunkingStrategy(ABC):
    """Base class for chunking strategies"""

    @abstractmethod
    def chunk(self, document: Document) -> List[Document]:
        raise NotImplementedError
