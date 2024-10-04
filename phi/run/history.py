from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from phi.run.response import RunResponse
from phi.model.message import Message


class RunHistory(BaseModel):
    message: Optional[Message] = None
    messages: Optional[List[Message]] = None
    response: Optional[RunResponse] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
