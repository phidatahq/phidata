from pathlib import Path
from abc import ABC, abstractmethod
from typing import Union

class GenericFileStorage(ABC):
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    @abstractmethod
    def serialize(self, data) -> None:
        pass

    @abstractmethod
    def deserialize(self):
        pass
