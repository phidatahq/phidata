from typing import Optional, Dict, Any

from pydantic import BaseModel


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
