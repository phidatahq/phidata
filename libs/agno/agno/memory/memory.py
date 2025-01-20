from typing import Optional

from pydantic import BaseModel


class Memory(BaseModel):
    """Model for Agent Memories"""

    memory: str
    id: Optional[str] = None
    topic: Optional[str] = None
    input: Optional[str] = None
