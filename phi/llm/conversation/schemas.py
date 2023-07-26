from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class ConversationRow(BaseModel):
    """Interface between Conversation class and the database"""

    # -*- Database ID/Primary key for this conversation.
    # This is set after the conversation is started and saved to the database.
    id: Optional[int] = None
    # -*- User data
    # The name of the user participating in this conversation.
    user_name: Optional[str] = None
    # The persona of the user participating in this conversation.
    user_persona: Optional[str] = None
    # True if this conversation is active i.e. not ended.
    is_active: Optional[bool] = None
    # -*- LLM data (name, model, etc.)
    llm: Optional[Dict[str, Any]] = None
    # -*- Conversation history
    history: Optional[Dict[str, Any]] = None
    # Usage data for this conversation.
    usage_data: Optional[Dict[str, Any]] = None
    # Extra data associated with this conversation.
    extra_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this conversation was created.
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated.
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
