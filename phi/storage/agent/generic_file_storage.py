import json
from pathlib import Path
from typing import Union, Any, Optional
from phi.storage.agent.base import AgentStorage
from phi.agent import AgentSession

class GenericFileStorage(AgentStorage):
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def create(self) -> None:
        """Create the storage if it doesn't exist."""
        if not self.path.exists():
            self.path.touch()

    def read(self, session_id: str, user_id: Optional[str] = None) -> Optional[AgentSession]:
        """Read an AgentSession from the storage."""
        if self.path.exists():
            data = self.deserialize()
            return AgentSession.model_validate(data.get(session_id)) if session_id in data else None
        return None

    def get_all_session_ids(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> list[str]:
        """Get all session IDs, optionally filtered by user_id and/or agent_id."""
        if self.path.exists():
            data = self.deserialize()
            return [sid for sid, session in data.items() if (not user_id or session['user_id'] == user_id) and (not agent_id or session['agent_id'] == agent_id)]
        return []

    def get_all_sessions(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> list[AgentSession]:
        """Get all sessions, optionally filtered by user_id and/or agent_id."""
        if self.path.exists():
            data = self.deserialize()
            return [AgentSession.model_validate(session) for session in data.values() if (not user_id or session['user_id'] == user_id) and (not agent_id or session['agent_id'] == agent_id)]
        return []

    def upsert(self, session: AgentSession, create_and_retry: bool = True) -> Optional[AgentSession]:
        """Insert or update an AgentSession in the storage."""
        data = self.deserialize() if self.path.exists() else {}
        data[session.session_id] = session.dict()
        self.serialize(data)
        return session

    def delete_session(self, session_id: Optional[str] = None):
        """Delete a session from the storage."""
        if session_id is None:
            return
        if self.path.exists():
            data = self.deserialize()
            if session_id in data:
                del data[session_id]
                self.serialize(data)

    def drop(self) -> None:
        """Drop the storage."""
        if self.path.exists():
            self.path.unlink()

    def upgrade_schema(self) -> None:
        """Upgrade the schema of the storage."""
        pass
