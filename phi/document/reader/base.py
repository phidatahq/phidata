from typing import Any, List, Optional

from pydantic import BaseModel

from phi.document.chunking.base import ChunkingStrategy
from phi.document.chunking.fixed import FixedChunking
from phi.document.base import Document


class Reader(BaseModel):
    chunk: bool = True
    chunk_size: int = 3000
    separators: List[str] = ["\n", "\n\n", "\r", "\r\n", "\n\r", "\t", " ", "  "]

    def __init__(self, chunking_strategy: Optional[ChunkingStrategy] = None):
        self.chunking_strategy = chunking_strategy or FixedChunking()

    def read(self, obj: Any) -> List[Document]:
        raise NotImplementedError

    def chunk_document(self, document: Document) -> List[Document]:
        return self.chunking_strategy.chunk(document)