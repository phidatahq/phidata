from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class ConversationRow(BaseModel):
    """Interface between Conversation class and the database"""

    # Conversation UUID
    id: str
    # Conversation name
    name: Optional[str] = None
    # User settings
    # Name and type of user participating in this conversation.
    user_name: Optional[str] = None
    user_type: Optional[str] = None
    # True if this conversation is active i.e. not ended
    is_active: Optional[bool] = None
    # LLM data (name, model, etc.)
    llm: Optional[Dict[str, Any]] = None
    # Conversation Memory
    memory: Optional[Dict[str, Any]] = None
    # Metadata associated with this conversation
    meta_data: Optional[Dict[str, Any]] = None
    # Extra data associated with this conversation
    extra_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this conversation was created
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    def serializable_dict(self):
        _dict = self.model_dump(exclude={"created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict

    def conversation_data(self) -> Dict[str, Any]:
        """Returns the conversation data as a dictionary."""
        _dict = self.model_dump(exclude={"memory", "created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict
