from typing import List, Optional, Union, Dict, Any

from phi.embedder.openai import OpenAIEmbedder
from phi.document.chunking.base import ChunkingStrategy
from phi.document.base import Document
from phi.embedder.base import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.utils.log import logger

try:
    from chonkie import SemanticChunker
except ImportError:
    logger.warning("`chonkie` is required for semantic chunking, please install using `pip install chonkie`")


class SemanticChunking(ChunkingStrategy):
    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        similarity_threshold: Optional[float] = 0.5,
        chunk_size: int = 5000,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedder = embedder or OpenAIEmbedder(model="text-embedding-3-small")
        self.similarity_threshold = similarity_threshold
        self.chunk_size = chunk_size

        # Initialize the chunker
        chunker_kwargs: Dict[str, Any] = {
            "chunk_size": self.chunk_size,
            "similarity_threshold": self.similarity_threshold,
        }
        if self.embedder is not None:
            chunker_kwargs["embedding_model"] = self.embedder.model
        self.chunker = SemanticChunker(**chunker_kwargs)

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
