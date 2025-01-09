from dataclasses import asdict, dataclass
from typing import Any, List, Optional


@dataclass
class File:
    name: Optional[str] = None
    description: Optional[str] = None
    columns: Optional[List[str]] = None
    path: Optional[str] = None
    type: str = "FILE"

    def get_metadata(self) -> dict[str, Any]:
        return asdict(self)
