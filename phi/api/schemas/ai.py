from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class ConversationType(str, Enum):
    RAG = "RAG"
    AUTO = "AUTO"


class ConversationClient(str, Enum):
    CLI = "CLI"
    WEB = "WEB"


class ConversationCreate(BaseModel):
    type: Optional[ConversationType] = ConversationType.RAG
    client: Optional[ConversationClient] = ConversationClient.CLI


class ConversationCreateResponse(BaseModel):
    id: int
    chat_history: List[Dict[str, Any]]


class ConversationChat(BaseModel):
    id: int
    message: str
    type: Optional[ConversationType] = ConversationType.RAG
    client: Optional[ConversationClient] = ConversationClient.CLI


class ConversationChatResponse(BaseModel):
    response: str
