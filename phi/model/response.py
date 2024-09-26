from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ModelResponseEvent(str, Enum):
    """Events that can be sent by the Model.response() method"""

    tool_call = "ToolCall"
    assistant_response = "ModelResponse"


class ModelResponse(BaseModel):
    """Response returned by Model.response()"""

    content: Optional[str] = None
    event: str = ModelResponseEvent.assistant_response.value
