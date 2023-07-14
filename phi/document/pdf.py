from pathlib import Path
from typing import List, Union

from phi.document.base import Document
from phi.document.reader.pdf import PDFReader
from phi.document.source import DocumentSource
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.utils.log import logger


class PDF(DocumentSource):
    path: Union[str, Path]
    reader: PDFReader = PDFReader()
    embedder: Embedder = OpenAIEmbedder()
    documents: List[Document] = []

    def read(self) -> None:
        """Convert the PDF into a list of Documents"""

        _path = self.path if isinstance(self.path, Path) else Path(self.path)
        self.documents = self.reader.read(path=_path)

    def embed(self) -> None:
        """Embed the documents in the PDF"""
        if self.documents is None:
            logger.warning(f"No documents to embed for PDF: {self.path}")
            return

        for document in self.documents:
            document.embed(embedder=self.embedder)

    def read_and_embed(self) -> None:
        """Read and embed the PDF"""

        self.read()
        self.embed()
