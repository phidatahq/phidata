from typing import Optional, Dict, Any, List

from pydantic import BaseModel, ConfigDict

from phi.embedder import Embedder


class Document(BaseModel):
    """Model for managing a document"""

    content: str
    source: Optional[str] = None
    meta_data: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    usage: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def embed(self, embedder: Embedder) -> None:
        """Embed the document using the provided embedder"""

        if embedder is None:
            raise ValueError("No embedder provided")

        self.embedding, self.usage = embedder.get_embedding_and_usage(self.content)
