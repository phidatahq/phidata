from pathlib import Path
from typing import Union, List, Iterator

from phi.document import Document
from phi.document.reader.pdf import PDFReader, PDFUrlReader
from phi.knowledge.base import KnowledgeBase


class PDFKnowledgeBase(KnowledgeBase):
    path: Union[str, Path]
    reader: PDFReader = PDFReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDFs and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        _pdf_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _pdf_path.exists() and _pdf_path.is_dir():
            for _pdf in _pdf_path.glob("**/*.pdf"):
                yield self.reader.read(pdf=_pdf)
        elif _pdf_path.exists() and _pdf_path.is_file() and _pdf_path.suffix == ".pdf":
            yield self.reader.read(pdf=_pdf_path)


class PDFUrlKnowledgeBase(KnowledgeBase):
    urls: List[str] = []
    reader: PDFUrlReader = PDFUrlReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDF urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for url in self.urls:
            yield self.reader.read(url=url)
