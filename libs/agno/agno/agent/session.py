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
        # Google Gemini adds a "parts" field to the messages, which is not serializable
        # If the provider is Google, remove the "parts" from the messages
        if self.agent_data is not None:
            if self.agent_data.get("model", {}).get("provider") == "Google" and self.memory is not None:
                # Remove parts from runs' response messages
                if "runs" in self.memory:
                    for _run in self.memory["runs"]:
                        if "response" in _run and "messages" in _run["response"]:
                            for m in _run["response"]["messages"]:
                                if isinstance(m, dict):
                                    m.pop("parts", None)

                # Remove parts from top-level memory messages
                if "messages" in self.memory:
                    for m in self.memory["messages"]:
                        if isinstance(m, dict):
                            m.pop("parts", None)

        monitoring_data = self.model_dump()
        return monitoring_data

    def telemetry_data(self) -> Dict[str, Any]:
        return self.model_dump(include={"model", "created_at", "updated_at"})
