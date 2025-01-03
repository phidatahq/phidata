from typing import Any, Dict, Optional
from pydantic import BaseModel


class Tool(BaseModel):
    """Model for Tools that can be used by an agent."""

    # The type of tool
    type: str
    # The function to be called if type = "function"
    function: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
