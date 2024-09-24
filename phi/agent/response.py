from time import time
from typing import Optional, Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from phi.model.message import Message, MessageContext


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
    created_at: int = Field(default_factory=lambda: int(time()))

    model_config = ConfigDict(arbitrary_types_allowed=True)
