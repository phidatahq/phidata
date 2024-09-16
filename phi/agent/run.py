from typing import Optional, Any, Dict, List
from pydantic import BaseModel


class RunResponse(BaseModel):
    """Data returned by Agent.run()"""

    run_id: str
    content: Any
    content_type: str = "str"
    messages: Optional[List[Dict[str, Any]]] = None
    metrics: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
