from typing import List, Optional

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.embedder import Embedder

from pydantic import BaseModel


class DocumentSource(BaseModel):
    """Model for managing a source of documents"""

    reader: Optional[Reader] = None
    embedder: Optional[Embedder] = None
    documents: List[Document] = []
