from typing import Any

from phi.file import File


class TextFile(File):
    path: str
    type: str = "TEXT"

    def get_metadata(self) -> dict[str, Any]:
        if self.name is None:
            from pathlib import Path

            self.name = Path(self.path).name
        return self.model_dump(exclude_none=True)
