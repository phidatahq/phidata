from typing import List, Optional, Any

from pydantic import BaseModel


class File(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    columns: Optional[List[str]] = None
    path: Optional[str] = None
    type: str = "FILE"

    def get_metadata(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
