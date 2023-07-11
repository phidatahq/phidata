from typing import Optional, Dict, Any

from pydantic import Field, BaseModel


class Document(BaseModel):
    """Model for storing document contents"""

    content: str
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
