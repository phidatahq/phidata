from time import time
from enum import Enum
from typing import Optional, Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from phi.model.message import Message, MessageContext


class RunEvent(str, Enum):
    """Events that can be sent by the run() functions"""

    run_started = "RunStarted"
    run_response = "RunResponse"
    run_completed = "RunCompleted"
    tool_call_started = "ToolCallStarted"
    tool_call_completed = "ToolCallCompleted"
    updating_memory = "UpdatingMemory"


class RunResponse(BaseModel):
    """Response returned by Agent.run() or Workflow.run() functions"""

    content: Optional[Any] = None
    content_type: str = "str"
    context: Optional[List[MessageContext]] = None
    event: str = RunEvent.run_response.value
    messages: Optional[List[Message]] = None
    metrics: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: int = Field(default_factory=lambda: int(time()))

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_content_as_string(self, **kwargs) -> str:
        import json

        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, BaseModel):
            return self.content.model_dump_json(exclude_none=True, **kwargs)
        else:
            return json.dumps(self.content, **kwargs)
