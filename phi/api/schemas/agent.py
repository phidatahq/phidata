from typing import Optional, Dict, Any

from pydantic import BaseModel


class AgentSessionCreate(BaseModel):
    """Data sent to API to create an Agent Session"""

    session_id: str
    agent_data: Optional[Dict[str, Any]] = None


class AgentRunCreate(BaseModel):
    """Data sent to API to create an Agent Run"""

    session_id: str
    agent_data: Optional[Dict[str, Any]] = None
    run_data: Optional[Dict[str, Any]] = None
