from typing import List, Optional

from pydantic import BaseModel


class ApiResponseData(BaseModel):
    status: str = "fail"
    message: str = "invalid request"
    message_log: Optional[List[str]] = None
