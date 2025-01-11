from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class WorkflowSession:
    """Workflow Session that is stored in the database"""

    # Session UUID
    session_id: str
    # ID of the workflow that this session is associated with
    workflow_id: Optional[str] = None
    # ID of the user interacting with this workflow
    user_id: Optional[str] = None
    # Workflow Memory
    memory: Optional[Dict[str, Any]] = None
    # Workflow Data
    workflow_data: Optional[Dict[str, Any]] = None
    # User Data
    user_data: Optional[Dict[str, Any]] = None
    # Session Data
    session_data: Optional[Dict[str, Any]] = None
    # The unix timestamp when this session was created
    created_at: Optional[int] = None
    # The unix timestamp when this session was last updated
    updated_at: Optional[int] = None

    def monitoring_data(self) -> Dict[str, Any]:
        return asdict(self)

    def telemetry_data(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
