from abc import ABC, abstractmethod
from typing import Optional, List

from phi.assistant.thread import AssistantThread


class AssistantStorage(ABC):
    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, thread_id: str) -> Optional[AssistantThread]:
        raise NotImplementedError

    @abstractmethod
    def get_all_thread_ids(self, user_id: Optional[str] = None) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_all_threads(self, user_id: Optional[str] = None) -> List[AssistantThread]:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, row: AssistantThread) -> Optional[AssistantThread]:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError
