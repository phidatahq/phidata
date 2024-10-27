import json
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Union, Any, Optional

class GenericFileStorage(ABC):
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def create(self, data: Any) -> None:
        """Create a new file with the given data."""
        if not self.path.exists():
            self.serialize(data)
        else:
            raise FileExistsError(f"File {self.path} already exists.")

    def read(self) -> Optional[Any]:
        """Read data from the file."""
        if self.path.exists():
            return self.deserialize()
        else:
            return None

    def update(self, data: Any) -> None:
        """Update the file with new data."""
        if self.path.exists():
            self.serialize(data)
        else:
            raise FileNotFoundError(f"File {self.path} does not exist.")

    def delete(self) -> None:
        """Delete the file."""
        if self.path.exists():
            self.path.unlink()
        else:
            raise FileNotFoundError(f"File {self.path} does not exist.")

    @abstractmethod
    def serialize(self, data) -> None:
        pass

    @abstractmethod
    def deserialize(self):
        pass
