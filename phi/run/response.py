import json
from time import time
from enum import Enum
from typing import Optional, Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from phi.model.content import Video, Image, Audio
from phi.reasoning.step import ReasoningStep
from phi.model.message import Message, MessageReferences


class RunEvent(str, Enum):
    """Events that can be sent by the run() functions"""

    run_started = "RunStarted"
    run_response = "RunResponse"
    run_completed = "RunCompleted"
    tool_call_started = "ToolCallStarted"
    tool_call_completed = "ToolCallCompleted"
    reasoning_started = "ReasoningStarted"
    reasoning_step = "ReasoningStep"
    reasoning_completed = "ReasoningCompleted"
    updating_memory = "UpdatingMemory"
    workflow_started = "WorkflowStarted"
    workflow_completed = "WorkflowCompleted"


class RunResponseExtraData(BaseModel):
    references: Optional[List[MessageReferences]] = None
    add_messages: Optional[List[Message]] = None
    history: Optional[List[Message]] = None
    reasoning_steps: Optional[List[ReasoningStep]] = None
    reasoning_messages: Optional[List[Message]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


class RunResponse(BaseModel):
    """Response returned by Agent.run() or Workflow.run() functions"""

    content: Optional[Any] = None
    content_type: str = "str"
    event: str = RunEvent.run_response.value
    messages: Optional[List[Message]] = None
    metrics: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    workflow_id: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    images: Optional[List[Image]] = None  # Images attached to the response
    videos: Optional[List[Video]] = None  # Videos attached to the response
    audio: Optional[List[Audio]] = None  # Audio attached to the response
    response_audio: Optional[Dict] = None  # Model audio response
    extra_data: Optional[RunResponseExtraData] = None
    created_at: int = Field(default_factory=lambda: int(time()))

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_json(self) -> str:
        _dict = self.model_dump(
            exclude_none=True,
            exclude={"messages"},
        )
        if self.messages is not None:
            _dict["messages"] = [
                m.model_dump(
                    exclude_none=True,
                    exclude={"parts"},  # Exclude what Gemini adds
                )
                for m in self.messages
            ]
        return json.dumps(_dict, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(
            exclude_none=True,
            exclude={"messages"},
        )
        if self.messages is not None:
            _dict["messages"] = [m.to_dict() for m in self.messages]
        return _dict

    def get_content_as_string(self, **kwargs) -> str:
        import json

        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, BaseModel):
            return self.content.model_dump_json(exclude_none=True, **kwargs)
        else:
            return json.dumps(self.content, **kwargs)
