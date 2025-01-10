from dataclasses import asdict, dataclass
from typing import Any

from agno.file import File


@dataclass
class TextFile(File):
    path: str = ""
    type: str = "TEXT"

    def get_metadata(self) -> dict[str, Any]:
        if self.name is None:
            from pathlib import Path

            self.name = Path(self.path).name
        return {k: v for k, v in asdict(self).items() if v is not None}
