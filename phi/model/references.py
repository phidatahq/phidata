from typing import Optional
from pydantic import BaseModel


class References(BaseModel):
    """Class for holing references added to user prompt for RAG"""

    # The question asked by the user.
    query: str
    # The references from the vector database.
    references: Optional[str] = None
    # Performance in seconds.
    time: Optional[float] = None
