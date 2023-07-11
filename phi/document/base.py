from typing import Optional, Dict, Any, List

from pydantic import Field, BaseModel


class Document(BaseModel):
    """Model for storing document contents"""

    content: str
    source: Optional[str] = None
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
