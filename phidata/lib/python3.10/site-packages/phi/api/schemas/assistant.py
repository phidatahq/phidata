from typing import Optional, Dict, Any

from pydantic import BaseModel


class AssistantWorkspace(BaseModel):
    id_workspace: Optional[int] = None
    ws_hash: Optional[str] = None
    ws_key: Optional[str] = None


class AssistantRunCreate(BaseModel):
    """Data sent to API to create an assistant run"""

    run_id: str
    assistant_data: Optional[Dict[str, Any]] = None


class AssistantEventCreate(BaseModel):
    """Data sent to API to create a new assistant event"""

    run_id: str
    assistant_data: Optional[Dict[str, Any]] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
