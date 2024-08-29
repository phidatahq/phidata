from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class AssistantThread(BaseModel):
    """Assistant Thread that can be used with a storage backend to store and retrieve assistant threads"""

    # Thread UUID
    thread_id: str
    # ID of the user participating in this run
    user_id: Optional[str] = None
    # LLM data (name, model, etc.)
    llm: Optional[Dict[str, Any]] = None
    # Assistant Memory
    memory: Optional[Dict[str, Any]] = None
    # Metadata associated with this assistant
    assistant_data: Optional[Dict[str, Any]] = None
    # Metadata associated with this thread
    thread_data: Optional[Dict[str, Any]] = None
    # Metadata associated the user participating in this run
    user_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this run was created
    created_at: Optional[datetime] = None
    # The timestamp of when this run was last updated
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    def serializable_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(exclude={"created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict

    def monitoring_data(self) -> Dict[str, Any]:
        _dict = self.model_dump(exclude={"created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict

    def telemetry_data(self) -> Dict[str, Any]:
        _dict = self.model_dump(include={"llm"}, exclude={"created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict
