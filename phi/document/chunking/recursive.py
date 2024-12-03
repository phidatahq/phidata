from typing import List

from phi.document.chunking.base import ChunkingStrategy


class RecursiveChunking(ChunkingStrategy):
    chunk_size: int = 5000
    overlap: int = 0
    
    def chunk(self, text: str) -> List[str]:
        """Recursively chunk text by finding natural break points"""
        if len(text) <= self.chunk_size:
            return [text]
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            if end < len(text):
                for sep in ["\n", "."]:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep != -1:
                        end = start + last_sep + 1
                        break
            
            chunk = text[start:end]
            chunks.append(chunk)
            
            start = max(start, end - self.overlap)
            
        return chunks
