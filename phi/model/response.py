from typing import Optional

from pydantic import BaseModel


class ModelResponse(BaseModel):
    """Response returned by Model.response()"""

    content: Optional[str] = None
