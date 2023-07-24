from abc import ABC, abstractmethod
from typing import Optional, Any


class LLMStorage(ABC):
    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_conversation(self, conversation_id: int, user_id: str) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def upsert_conversation(self, conversation: Any) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def end_conversation(self, conversation_id: int, user_id: str) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError
