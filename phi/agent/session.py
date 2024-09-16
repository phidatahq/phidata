from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class AgentSession(BaseModel):
    """Agent Session that is stored in the database"""

    # Session UUID
    session_id: str
    # ID of the user interacting with this agent
    user_id: Optional[str] = None
    # Model data (name, model, etc.)
    model: Optional[Dict[str, Any]] = None
    # Agent Memory
    memory: Optional[Dict[str, Any]] = None
    # Agent Metadata
    agent_data: Optional[Dict[str, Any]] = None
    # User Metadata
    user_data: Optional[Dict[str, Any]] = None
    # Session Metadata
    session_data: Optional[Dict[str, Any]] = None
    # The timestamp of when this session was created
    created_at: Optional[datetime] = None
    # The timestamp of when this session was last updated
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    def monitoring_data(self) -> Dict[str, Any]:
        _dict = self.model_dump(exclude={"created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict

    def telemetry_data(self) -> Dict[str, Any]:
        _dict = self.model_dump(include={"model"}, exclude={"created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict
