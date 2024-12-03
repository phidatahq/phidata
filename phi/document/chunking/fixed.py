from typing import List

from phi.document.chunking.base import ChunkingStrategy


class FixedChunking(ChunkingStrategy):
    chunk_size: int = 5000
    overlap: int = 0

    def chunk(self, text: str) -> List[str]:
        """Split text into fixed-size chunks with optional overlap"""
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)

            chunk = text[start:end]
            chunks.append(chunk)

            start = end - self.overlap

        return chunks
