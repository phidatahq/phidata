from typing import Any, Dict
from pydantic import BaseModel


class BaseTool(BaseModel):
    """Model for LLM Tools"""

    # The type of tool
    type: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
