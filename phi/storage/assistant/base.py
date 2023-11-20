from abc import ABC, abstractmethod
from typing import Optional, List

from phi.assistant.row import AssistantRow


class AssistantStorage(ABC):
    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, conversation_id: str) -> Optional[AssistantRow]:
        raise NotImplementedError

    @abstractmethod
    def get_all_conversation_ids(self, user_name: Optional[str] = None) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_all_conversations(self, user_name: Optional[str] = None) -> List[AssistantRow]:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, conversation: AssistantRow) -> Optional[AssistantRow]:
        raise NotImplementedError

    @abstractmethod
    def end(self, conversation_id: str) -> Optional[AssistantRow]:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError
