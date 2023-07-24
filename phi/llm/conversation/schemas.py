from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict

from phi.llm.history.base import LLMHistory


class ConversationRow(BaseModel):
    """Pydantic model for holding LLM conversations"""

    # The ID of this conversation. Added after the conversation is created.
    id: Optional[int] = None
    # The name of this conversation. Added after the conversation is created.
    name: Optional[str] = None
    # Required: The ID of the user who is participating in this conversation.
    user_id: str
    # Required: The history for this conversation.
    history: LLMHistory
    # The persona of the user who is participating in this conversation.
    user_persona: Optional[str] = None
    # The data of the user who is participating in this conversation.
    user_data: Optional[Dict[str, Any]] = None
    # True if this conversation is active.
    is_active: Optional[bool] = None
    # The usage data of this conversation.
    usage_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this conversation was created.
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated.
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
