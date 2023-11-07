from typing import Any, Dict, Optional
from pydantic import BaseModel


class Tool(BaseModel):
    """Model for Assistant Tools"""

    # The type of tool
    type: str
    function: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
