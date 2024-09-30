from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass


class ModelResponseEvent(str, Enum):
    """Events that can be sent by the Model.response() method"""

    tool_call = "ToolCall"
    assistant_response = "AssistantResponse"


@dataclass
class ModelResponse:
    """Response returned by Model.response()"""

    content: Optional[str] = None
    parsed: Optional[Any] = None
    event: str = ModelResponseEvent.assistant_response.value
