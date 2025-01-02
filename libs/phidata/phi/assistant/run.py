from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class AssistantRun(BaseModel):
    """Assistant Run that is stored in the database"""

    # Assistant name
    name: Optional[str] = None
    # Run UUID
    run_id: str
    # Run name
    run_name: Optional[str] = None
    # ID of the user participating in this run
    user_id: Optional[str] = None
    # LLM data (name, model, etc.)
    llm: Optional[Dict[str, Any]] = None
    # Assistant Memory
    memory: Optional[Dict[str, Any]] = None
    # Metadata associated with this assistant
    assistant_data: Optional[Dict[str, Any]] = None
    # Metadata associated with this run
    run_data: Optional[Dict[str, Any]] = None
    # Metadata associated the user participating in this run
    user_data: Optional[Dict[str, Any]] = None
    # Metadata associated with the assistant tasks
    task_data: Optional[Dict[str, Any]] = None
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

    def assistant_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(exclude={"created_at", "updated_at", "task_data"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict
