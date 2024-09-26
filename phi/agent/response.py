from time import time
from enum import Enum
from typing import Optional, Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from phi.model.message import Message, MessageContext


class RunEvent(str, Enum):
    """Events that can be sent by the Agent.run() method"""

    run_start = "RunStart"
    intermediate_step = "IntermediateStep"
    agent_response = "AgentResponse"
    run_end = "RunEnd"


class RunResponse(BaseModel):
    """Response returned by Agent.run()"""

    run_id: str
    content: Optional[Any] = None
    content_type: str = "str"
    messages: Optional[List[Message]] = None
    metrics: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    context: Optional[List[MessageContext]] = None
    model: Optional[str] = None
    event: RunEvent = RunEvent.agent_response
    created_at: int = Field(default_factory=lambda: int(time()))

    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)
