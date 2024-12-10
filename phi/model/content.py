from typing import Optional

from pydantic import BaseModel

class Video(BaseModel):
    id: str
    url: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None
    eta: Optional[str] = None

class Image(BaseModel):
    id: str
    url: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None
