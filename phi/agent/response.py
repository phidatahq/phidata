from typing import Optional, Any, Dict, List

from pydantic import BaseModel, ConfigDict

from phi.model.message import Message


class RunResponse(BaseModel):
    """Response returned by Agent.run()"""

    run_id: str
    content: Optional[Any] = None
    content_type: str = "str"
    messages: Optional[Message] = None
    metrics: Optional[Dict[str, Any]] = None
    model: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
