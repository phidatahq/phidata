from enum import Enum

from pydantic import BaseModel, ConfigDict


class RetrievalStrategy(str, Enum):
    semantic = "semantic"


class Retriever(BaseModel):
    num_documents: int = 2
    strategy: RetrievalStrategy = RetrievalStrategy.semantic

    model_config = ConfigDict(arbitrary_types_allowed=True)
