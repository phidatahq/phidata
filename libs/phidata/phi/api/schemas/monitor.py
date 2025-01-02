from typing import Any, Dict, Optional

from pydantic import BaseModel


class MonitorEventSchema(BaseModel):
    event_type: str
    event_status: str
    object_name: str
    event_data: Optional[Dict[str, Any]] = None
    object_data: Optional[Dict[str, Any]] = None


class MonitorResponseSchema(BaseModel):
    id_monitor: Optional[int] = None
    id_event: Optional[int] = None
