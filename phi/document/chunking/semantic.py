from typing import List, Optional

from phi.document.chunking.strategy import ChunkingStrategy
from phi.document.base import Document
from phi.embedder.base import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.utils.log import logger

try:
    from chonkie import SemanticChunker
except ImportError:
    logger.warning("`chonkie` is required for semantic chunking, please install using `pip install chonkie`")


class SemanticChunking(ChunkingStrategy):
    """Chunking strategy that splits text into semantic chunks using chonkie"""

    def __init__(
        self, embedder: Optional[Embedder] = None, chunk_size: int = 5000, similarity_threshold: Optional[float] = 0.5
    ):
        self.embedder = embedder or OpenAIEmbedder(model="text-embedding-3-small")
        self.chunk_size = chunk_size
        self.similarity_threshold = similarity_threshold
        self.chunker = SemanticChunker(
            embedding_model=self.embedder.model,  # type: ignore
            chunk_size=self.chunk_size,
            similarity_threshold=self.similarity_threshold,
        )

    def chunk(self, document: Document) -> List[Document]:
        """Split document into semantic chunks using chokie"""
        if not document.content:
            return [document]

        # Use chonkie to split into semantic chunks
        chunks = self.chunker.chunk(self.clean_text(document.content))

        # Convert chunks to Documents
        chunked_documents: List[Document] = []
        for i, chunk in enumerate(chunks, 1):
            meta_data = document.meta_data.copy()
            meta_data["chunk"] = i
            chunk_id = f"{document.id}_{i}" if document.id else None
            meta_data["chunk_size"] = len(chunk.text)

            chunked_documents.append(Document(id=chunk_id, name=document.name, meta_data=meta_data, content=chunk.text))

        return chunked_documents
