from typing import List, Optional, Iterator

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.embedder import Embedder

from pydantic import BaseModel, ConfigDict


class DocumentSource(BaseModel):
    """Model for managing a source of documents"""

    reader: Optional[Reader] = None
    embedder: Optional[Embedder] = None
    documents: List[Document] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def read(self) -> Iterator[Document]:
        """Read the source of documents"""
        raise NotImplementedError
