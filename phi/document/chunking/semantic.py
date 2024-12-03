from typing import List, Optional
from chokie import SemanticChunker
from phi.document.chunking.base import ChunkingStrategy
from phi.embedder.base import Embedder
from phi.embedder.openai import OpenAIEmbedder


class SemanticChunking(ChunkingStrategy):

    def __init__(self, chunk_size: int = 5000, similarity_threshold: Optional[float] = 0.5, embedding_model: Optional[Embedder] = None, initial_sentences: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.similarity_threshold = similarity_threshold
        self.embedding_model = embedding_model or OpenAIEmbedder(model="text-embedding-3-small")
        self.initial_sentences = initial_sentences

    def chunk(self, text: str) -> List[str]:
        """Split text into semantic chunks using chokie's SemanticChunker"""
        chunker = SemanticChunker(
            chunk_size=self.chunk_size,
            similarity_threshold=self.similarity_threshold,
            embedding_model=self.embedding_model,
            initial_sentences=self.initial_sentences
        )
        chunks = chunker.split(text)
        return [chunk.text for chunk in chunks]
