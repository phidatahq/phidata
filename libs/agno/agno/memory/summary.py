from typing import List, Optional

from pydantic import BaseModel, Field


class SessionSummary(BaseModel):
    """Model for Session Summary."""

    summary: str = Field(
        ...,
        description="Summary of the session. Be concise and focus on only important information. Do not make anything up.",
    )
    topics: Optional[List[str]] = Field(None, description="Topics discussed in the session.")
