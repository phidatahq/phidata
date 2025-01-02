from typing import Any, List

from pydantic import BaseModel, Field, ConfigDict

from phi.document.chunking.strategy import ChunkingStrategy
from phi.document.chunking.fixed import FixedSizeChunking
from phi.document.base import Document


class Reader(BaseModel):
    """Base class for reading documents"""

    chunk: bool = True
    chunk_size: int = 3000
    separators: List[str] = ["\n", "\n\n", "\r", "\r\n", "\n\r", "\t", " ", "  "]
    chunking_strategy: ChunkingStrategy = Field(default_factory=FixedSizeChunking)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def read(self, obj: Any) -> List[Document]:
        raise NotImplementedError

    def chunk_document(self, document: Document) -> List[Document]:
        return self.chunking_strategy.chunk(document)
