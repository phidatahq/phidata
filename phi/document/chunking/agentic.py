from typing import List, Optional
from phi.document.chunking.base import ChunkingStrategy
from phi.model.openai import OpenAIChat
from phi.model.base import Model


class AgenticChunking(ChunkingStrategy):

    def __init__(self, model: Optional[Model] = None, max_chunk_size: int = 5000, **kwargs):
        super().__init__(**kwargs)
        self.model = model or OpenAIChat()
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str) -> List[str]:
        """Split text into chunks using LLM to determine natural breakpoints based on context"""
        if len(text) <= self.max_chunk_size:
            return [text]

        chunks = []
        remaining_text = text

        while remaining_text:
            # Ask model to find a good breakpoint within max_chunk_size
            prompt = f"""Analyze this text and determine a natural breakpoint within the first {self.max_chunk_size} characters. 
            Consider semantic completeness, paragraph boundaries, and topic transitions.
            Return only the character position number of where to break the text:
            
            {remaining_text[:self.max_chunk_size]}"""
            
            try:
                response = self.model.response(prompt)
                break_point = min(int(response.strip()), self.max_chunk_size)
            except:
                # Fallback to max size if model fails
                break_point = self.max_chunk_size

            # Extract chunk and update remaining text
            chunk = remaining_text[:break_point].strip()
            if chunk:
                chunks.append(chunk)
            
            remaining_text = remaining_text[break_point:].strip()
            
            if not remaining_text:
                break

        return chunks
