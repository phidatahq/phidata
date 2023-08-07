from typing import Optional, Dict, Any

from pydantic import BaseModel


class ConversationEventCreate(BaseModel):
    """Data sent to API to create a new conversation event"""

    id_user: Optional[int] = None
    conversation_key: str
    conversation_data: Optional[Dict[str, Any]] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None


class ConversationWorkspace(BaseModel):
    id_workspace: int
    ws_hash: Optional[str] = None


class ConversationResponseSchema(BaseModel):
    id_event: Optional[int] = None
    id_conversation: Optional[int] = None
