from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict


class AssistantRow(BaseModel):
    """Interface between OpenAIAssistant class and the database"""

    # OpenAIAssistant id which can be referenced in API endpoints.
    id: str
    # The object type, which is always assistant.
    object: str
    # The name of the assistant. The maximum length is 256 characters.
    name: Optional[str] = None
    # The description of the assistant. The maximum length is 512 characters.
    description: Optional[str] = None
    # The system instructions that the assistant uses. The maximum length is 32768 characters.
    instructions: Optional[str] = None
    # LLM data (name, model, etc.)
    llm: Optional[Dict[str, Any]] = None
    # OpenAIAssistant Tools
    tools: Optional[List[Dict[str, Any]]] = None
    # Files attached to this assistant.
    files: Optional[List[Dict[str, Any]]] = None
    # Metadata attached to this assistant.
    metadata: Optional[Dict[str, Any]] = None
    # OpenAIAssistant Memory
    memory: Optional[Dict[str, Any]] = None
    # True if this assistant is active
    is_active: Optional[bool] = None
    # The timestamp of when this conversation was created
    created_at: Optional[datetime] = None
    # The timestamp of when this conversation was last updated
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    def serializable_dict(self):
        _dict = self.model_dump(exclude={"created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict

    def assistant_data(self) -> Dict[str, Any]:
        """Returns the assistant data as a dictionary."""
        _dict = self.model_dump(exclude={"memory", "created_at", "updated_at"})
        _dict["created_at"] = self.created_at.isoformat() if self.created_at else None
        _dict["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return _dict
