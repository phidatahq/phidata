from typing import Any, Dict, Optional

from pydantic import BaseModel


class MonitorEventSchema(BaseModel):
    object_name: Optional[str] = None
    object_data: Optional[Dict[str, Any]] = None
    event_data: Optional[Dict[str, Any]] = None


class MonitorResponseSchema(BaseModel):
    id_monitor: Optional[int] = None
    id_event: Optional[int] = None
