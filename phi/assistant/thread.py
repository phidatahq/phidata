from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import BaseModel, ConfigDict

from phi.llm.base import LLM
from phi.llm.openai import OpenAIChat


class Thread(BaseModel):
    llm: LLM = OpenAIChat()

    # -*- Thread settings
    # Thread id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always thread.
    object: Optional[str] = None
    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maxium of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    # True if this assistant is active
    is_active: bool = True
    # The timestamp of when this assistant was created in the database
    created_at: Optional[datetime] = None
    # The timestamp of when this assistant was last updated in the database
    updated_at: Optional[datetime] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)
