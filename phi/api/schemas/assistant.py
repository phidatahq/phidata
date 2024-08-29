from typing import Optional, Dict, Any

from pydantic import BaseModel


class AssistantThreadCreate(BaseModel):
    """Data sent to API to create an assistant thread"""

    thread_id: str
    assistant_data: Optional[Dict[str, Any]] = None


class AssistantRunCreate(BaseModel):
    """Data sent to API to create a new assistant event"""

    thread_id: str
    assistant_data: Optional[Dict[str, Any]] = None
    run_data: Optional[Dict[str, Any]] = None
