from time import time
from enum import Enum
from typing import Optional, Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class WorkflowEvent(str, Enum):
    """Events that can be sent by Workflow.run()"""

    run_started = "RunStarted"
    agent_response = "AgentResponse"
    run_completed = "RunCompleted"


class WorkflowResponse(BaseModel):
    """Response returned by Workflow.run()"""

    run_id: str
    workflow_id: str
    content: Optional[Any] = None
    content_type: str = "str"
    event: str = WorkflowEvent.agent_response.value
    event_data: Optional[Dict[str, Any]] = None
    created_at: int = Field(default_factory=lambda: int(time()))

    model_config = ConfigDict(arbitrary_types_allowed=True)
