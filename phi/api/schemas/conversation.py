from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel


class ConversationWorkspace(BaseModel):
    id_workspace: int
    ws_hash: Optional[str] = None


class ConversationEventCreate(BaseModel):
    """Data sent to API to create a new conversation event"""

    id_user: Optional[int] = None
    conversation_key: str
    conversation_data: Optional[Dict[str, Any]] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None


class ConversationEventCreateResopnse(BaseModel):
    id_event: Optional[int] = None
    id_conversation: Optional[int] = None


class ConversationUpdate(BaseModel):
    """Data sent to API to update a conversation"""

    conversation_key: str
    conversation_data: Optional[Dict[str, Any]] = None


class ConversationSchema(BaseModel):
    """Schema for a conversation returned by API"""

    id_conversation: Optional[int] = None
    id_workspace: Optional[int] = None
    conversation_key: Optional[str] = None
    conversation_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
