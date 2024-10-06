from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class AgentSession(BaseModel):
    """Agent Session that is stored in the database"""

    # Session UUID
    session_id: str
    # ID of the agent that this session is associated with
    agent_id: Optional[str] = None
    # ID of the user interacting with this agent
    user_id: Optional[str] = None
    # Agent Memory
    memory: Optional[Dict[str, Any]] = None
    # Agent Metadata
    agent_data: Optional[Dict[str, Any]] = None
    # User Metadata
    user_data: Optional[Dict[str, Any]] = None
    # Session Metadata
    session_data: Optional[Dict[str, Any]] = None
    # The Unix timestamp when this session was created
    created_at: Optional[int] = None
    # The Unix timestamp when this session was last updated
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    def monitoring_data(self) -> Dict[str, Any]:
        return self.model_dump()

    def telemetry_data(self) -> Dict[str, Any]:
        return self.model_dump(include={"model", "created_at", "updated_at"})
