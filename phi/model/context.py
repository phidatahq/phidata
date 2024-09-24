from typing import Optional
from pydantic import BaseModel


class Context(BaseModel):
    """The context added to user message for RAG"""

    # The query used to retrieve the context.
    query: str
    # The content from the vector database.
    content: Optional[str] = None
    # Performance in seconds.
    time: Optional[float] = None
