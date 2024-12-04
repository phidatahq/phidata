from typing import List, Optional

from phi.document.chunking.base import ChunkingStrategy
from phi.document.base import Document
from phi.embedder.base import Embedder
from phi.embedder.openai import OpenAIEmbedder

from chokie import SemanticChunker


class SemanticChunking(ChunkingStrategy):
    def __init__(
        self,
        embedding_model: Optional[Embedder] = None,
        chunk_size: int = 5000,
        similarity_threshold: Optional[float] = 0.5,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedding_model = embedding_model or OpenAIEmbedder(model="text-embedding-3-small")
        self.chunk_size = chunk_size
        self.similarity_threshold = similarity_threshold
        self.chunker = SemanticChunker(
            embedding_model=self.embedding_model,
            max_chunk_size=self.chunk_size,
            similarity_threshold=self.similarity_threshold,
        )

    def chunk(self, document: Document) -> List[Document]:
        """Split document into semantic chunks using chokie"""
        if not document.content:
            return [document]

        # Use chokie to split into semantic chunks
        chunks = self.chunker.chunk(document.content)

        # Convert chunks to Documents
        chunked_documents: List[Document] = []
        for i, chunk in enumerate(chunks, 1):
            meta_data = document.meta_data.copy()
            meta_data["chunk"] = i
            chunk_id = f"{document.id}_{i}" if document.id else None
            meta_data["chunk_size"] = len(chunk)

            chunked_documents.append(Document(id=chunk_id, name=document.name, meta_data=meta_data, content=chunk))

        return chunked_documents
