from typing import Optional, Dict, Any

from pydantic import BaseModel


class ConversationWorkspace(BaseModel):
    id_workspace: Optional[int] = None
    ws_hash: Optional[str] = None
    ws_key: Optional[str] = None


class ConversationMonitorCreate(BaseModel):
    """Data sent to API to create a conversation monitor"""

    conversation_id: str
    conversation_data: Optional[Dict[str, Any]] = None


class ConversationEventCreate(BaseModel):
    """Data sent to API to create a new conversation event"""

    conversation_id: str
    conversation_data: Optional[Dict[str, Any]] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
