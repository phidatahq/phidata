from abc import ABC, abstractmethod
from typing import Optional, List

from phi.conversation.schemas import ConversationRow


class ConversationStorage(ABC):
    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, conversation_id: int) -> Optional[ConversationRow]:
        raise NotImplementedError

    @abstractmethod
    def get_all_conversation_ids(self, user_name: str) -> List[int]:
        raise NotImplementedError

    @abstractmethod
    def get_all_conversations(self, user_name: str) -> List[ConversationRow]:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, conversation: ConversationRow) -> Optional[ConversationRow]:
        raise NotImplementedError

    @abstractmethod
    def end(self, conversation_id: int) -> Optional[ConversationRow]:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError
