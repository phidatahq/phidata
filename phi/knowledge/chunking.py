from typing import List

from pydantic import BaseModel


class ChunkingStrategy(BaseModel):
    pass


class CharacterChunks(ChunkingStrategy):
    chunk_size: int = 5000
    separators: List[str] = ["\n", "\n\n", "\r", "\r\n", "\n\r", "\t", " ", "  "]
