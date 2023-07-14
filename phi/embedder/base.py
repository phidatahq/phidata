from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Tuple


class Embedder(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError

    @abstractmethod
    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        raise NotImplementedError
