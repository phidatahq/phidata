import json
from pathlib import Path
from typing import Union, Any, Optional
from abc import abstractmethod
from urllib.parse import quote
from phi.storage.agent.base import AgentStorage
from phi.agent import AgentSession

class GenericFileStorage(AgentStorage):
    def __init__(self, path: Union[str, Path], use_by_name: bool = True):
        self.base_path = Path(path)
        self.by_id_path = self.base_path / "by_id"
        self.by_name_path = self.base_path / "by_name"
        self.by_id_path.mkdir(parents=True, exist_ok=True)
        if use_by_name:
            self.by_name_path.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def fileExtension(self) -> str:
        """Return the file extension used by the storage."""
        raise NotImplementedError

    @abstractmethod
    def serialize(self, data: Any) -> str:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self) -> Any:
        raise NotImplementedError

    def create(self) -> None:
        """Create the storage if it doesn't exist."""
        if not self.by_id_path.exists():
            self.by_id_path.mkdir(parents=True, exist_ok=True)

    def read(self, session_id: str, user_id: Optional[str] = None) -> Optional[AgentSession]:
        """Read an AgentSession from the storage."""
        session_file = self.by_id_path / f"{session_id}{self.fileExtension}"
        if session_file.exists():
            data = self.deserialize(session_file)
            return AgentSession.model_validate(data)
        return None

    def get_all_session_ids(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> list[str]:
        """Get all session IDs, optionally filtered by user_id and/or agent_id."""
        session_files = self.by_id_path.glob("*.json")
        session_ids = []
        for session_file in session_files:
            data = self.deserialize(session_file)
            if (not user_id or data['user_id'] == user_id) and (not agent_id or data['agent_id'] == agent_id):
                session_ids.append(data['session_id'])
        return session_ids

    def get_all_session_ids_and_names(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> list[tuple[str, str]]:
        """Get all session IDs and their names, optionally filtered by user_id and/or agent_id."""
        session_files = self.by_id_path.glob("*.json")
        session_ids_and_names = []
        for session_file in session_files:
            data = self.deserialize(session_file)
            if (not user_id or data['user_id'] == user_id) and (not agent_id or data['agent_id'] == agent_id):
                session_id = data['session_id']
                name = data.get('agent_data', {}).get('name', 'unknown')
                session_ids_and_names.append((session_id, name))
        return session_ids_and_names

    def get_all_sessions(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> list[AgentSession]:
        """Get all sessions, optionally filtered by user_id and/or agent_id."""
        session_files = self.by_id_path.glob("*.json")
        sessions = []
        for session_file in session_files:
            data = self.deserialize(session_file)
            if (not user_id or data['user_id'] == user_id) and (not agent_id or data['agent_id'] == agent_id):
                sessions.append(AgentSession.model_validate(data))
        return sessions

    def upsert(self, session: AgentSession, create_and_retry: bool = True) -> Optional[AgentSession]:
        """Insert or update an AgentSession in the storage."""
        session_file = self.by_id_path / f"{session.session_id}{self.fileExtension}"
        self.serialize(session.dict(), session_file)

        # Create a symlink in the by_name directory
        if self.by_name_path.exists():
            name = session.agent_data.get('name', 'unknown')
            symlink_name = f"{quote(name)}#{quote(session.session_id)}"
            symlink_path = self.by_name_path / symlink_name
            if not symlink_path.exists():
                symlink_path.symlink_to(session_file)

        return session

    def delete_session(self, session_id: Optional[str] = None):
        """Delete a session from the storage."""
        if session_id is None:
            return
        session_file = self.by_id_path / f"{session_id}{self.fileExtension}"
        if session_file.exists():
            session_file.unlink()

    def drop(self) -> None:
        """Drop the storage."""
        if self.by_id_path.exists():
            for session_file in self.by_id_path.glob(f"*{self.fileExtension}"):
                session_file.unlink()

    def upgrade_schema(self) -> None:
        """Upgrade the schema of the storage."""
        pass
