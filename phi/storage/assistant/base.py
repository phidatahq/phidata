from abc import ABC, abstractmethod
from typing import Optional, List

from phi.assistant.row import AssistantRow


class AssistantStorage(ABC):
    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, run_id: str) -> Optional[AssistantRow]:
        raise NotImplementedError

    @abstractmethod
    def get_all_run_ids(self, user_id: Optional[str] = None) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_all_runs(self, user_id: Optional[str] = None) -> List[AssistantRow]:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, row: AssistantRow) -> Optional[AssistantRow]:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> None:
        raise NotImplementedError
