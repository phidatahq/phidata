from datetime import datetime
from typing import List, Any, Optional, Dict

from pydantic import BaseModel, ConfigDict

from phi.assistant.tool import Tool
from phi.assistant.row import AssistantRow
from phi.assistant.storage import AssistantStorage
from phi.knowledge.base import KnowledgeBase
from phi.llm.base import LLM
from phi.llm.openai import GPT

from phi.utils.log import logger, set_log_level_to_debug
from phi.utils.timer import Timer


class Assistant(BaseModel):
    llm: LLM = GPT()

    # -*- Assistant settings
    # Assistant id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always assistant.
    object: Optional[str] = None
    # The name of the assistant. The maximum length is 256 characters.
    name: Optional[str] = None
    # The description of the assistant. The maximum length is 512 characters.
    description: Optional[str] = None
    # The system instructions that the assistant uses. The maximum length is 32768 characters.
    instructions: Optional[str] = None

    # -*- Assistant Tools
    # A list of tool enabled on the assistant. There can be a maximum of 128 tools per assistant.
    # Tools can be of types code_interpreter, retrieval, or function.
    tools: Optional[List[Tool]] = None

    # -*- Assistant Files
    # A list of file IDs attached to this assistant.
    # There can be a maximum of 20 files attached to the assistant.
    # Files are ordered by their creation date in ascending order.
    file_ids: Optional[List[Any]] = None
    # Files attached to this assistant.
    files: Optional[List[Any]] = None

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

    # -*- Assistant Memory
    memory: Optional[Any] = None

    # -*- Assistant Storage
    storage: Optional[AssistantStorage] = None
    # Create table if it doesn't exist
    create_storage: bool = True
    # AssistantRow from the database: DO NOT SET THIS MANUALLY
    database_row: Optional[AssistantRow] = None

    # -*- Assistant Knowledge Base
    knowledge_base: Optional[KnowledgeBase] = None

    # -*- Latest LLM response
    output: Optional[Any] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)
