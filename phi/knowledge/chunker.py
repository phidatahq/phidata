from enum import Enum
from typing import List

from pydantic import BaseModel


class ChunkStrategy(str, Enum):
    simple = "simple"


class Chunker(BaseModel):
    enabled: bool = True
    chunk_size: int = 3000
    strategy: ChunkStrategy = ChunkStrategy.simple
    separators: List[str] = ["\n", "\n\n", "\r", "\r\n", "\n\r", "\t", " ", "  "]
