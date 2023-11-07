from datetime import datetime
from typing import List, Any, Optional, Dict

from pydantic import BaseModel


class Message(BaseModel):
    """Model for Assistant messages"""

    # -*- Message settings
    # Message id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always thread.message.
    object: Optional[str] = None

    # The entity that produced the message. One of user or assistant.
    role: str
    # The content of the message in array of text and/or images.
    content: List[Any] | str

    # The thread ID that this message belongs to.
    thread_id: Optional[str] = None
    # If applicable, the ID of the assistant that authored this message.
    assistant_id: Optional[str] = None
    # If applicable, the ID of the run associated with the authoring of this message.
    run_id: Optional[str] = None
    # A list of file IDs that the assistant should use.
    # Useful for tools like retrieval and code_interpreter that can access files.
    # A maximum of 10 files can be attached to a message.
    file_ids: Optional[List[Any]] = None
    # Files attached to this message.
    files: Optional[List[Any]] = None

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maxium of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    # The timestamp of when this assistant was created in the database
    created_at: Optional[datetime] = None
