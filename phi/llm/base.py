from abc import ABC, abstractmethod
from typing import List, Iterator


class LLM(ABC):
    @abstractmethod
    def response(self, messages: List) -> str:
        raise NotImplementedError

    @abstractmethod
    def streaming_response(self, messages: List) -> Iterator[str]:
        raise NotImplementedError
