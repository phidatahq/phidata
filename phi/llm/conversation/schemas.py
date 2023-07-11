from pydantic import BaseModel


class Message(BaseModel):
    """
    Message class for holding LLM messages.
    """

    role: str
    content: str
