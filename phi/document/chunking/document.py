from typing import List
from phi.document.chunking.base import ChunkingStrategy


class DocumentChunking(ChunkingStrategy):
    """A chunking strategy that splits text based on document structure like paragraphs and sections"""
    
    def __init__(self, chunk_size: int = 5000, overlap: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        """Split text into chunks based on document structure"""
        if len(text) <= self.chunk_size:
            return [text]
            
        # Split on double newlines first (paragraphs)
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            para_size = len(para)
            
            if current_size + para_size <= self.chunk_size:
                current_chunk.append(para)
                current_size += para_size
            else:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
                
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        # Handle overlap if specified
        if self.overlap > 0:
            overlapped_chunks = []
            for i in range(len(chunks)):
                if i > 0:
                    # Add overlap from previous chunk
                    prev_text = chunks[i-1][-self.overlap:]
                    if prev_text:
                        overlapped_chunks.append(prev_text + chunks[i])
                else:
                    overlapped_chunks.append(chunks[i])
            chunks = overlapped_chunks
            
        return chunks
