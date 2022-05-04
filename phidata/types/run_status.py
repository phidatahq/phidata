from pydantic import BaseModel


class RunStatus(BaseModel):
    name: str
    success: bool = False
