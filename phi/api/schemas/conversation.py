from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class ConversationEventSchema(BaseModel):
    id_user: Optional[int] = None
    id_workspace: int
    conversation_key: str
    conversation_data: Optional[Dict[str, Any]] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None


class ConversationResponseSchema(BaseModel):
    id_event: Optional[int] = None
    id_conversation: Optional[int] = None
