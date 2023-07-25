from pathlib import Path
from typing import List

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger


class PDFReader(Reader):
    """Reader for PDF files"""

    def read(self, path: Path) -> List[Document]:
        if not path:
            raise ValueError("No path provided")

        if not path.exists():
            raise FileNotFoundError(f"Could not find file: {path}")

        try:
            from pypdf import PdfReader as DocumentReader  # noqa: F401
        except ImportError:
            raise ImportError("`pypdf` not installed")

        try:
            logger.info(f"Reading: {path}")
            doc_name = path.name.split(".")[0]
            doc_reader = DocumentReader(path)

            documents = [
                Document(
                    name=doc_name,
                    meta_data={"page": page_number},
                    content=page.extract_text(),
                )
                for page_number, page in enumerate(doc_reader.pages, start=1)
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document))
                return chunked_documents
            return documents
        except Exception:
            raise


# def read_pdfs_from_dir(dir: Path) -> List[Document]:
#     """Read data from a PDF and return a list of Documents"""
#
#     logger.info(f"Reading PDFs in: {dir}")
#     pdfs_to_read: List[Path] = []
#     for pdf in dir.glob("*.pdf"):
#         pdfs_to_read.append(pdf)
#     logger.info(f"Found {len(pdfs_to_read)} PDFs to read")
#
#     reader = PDFReader()
#     parsed_pdfs: List[Document] = []
#     for pdf in pdfs_to_read:
#         # Parse the PDF document
#         documents: Optional[List[Document]] = reader.read(path=pdf)
#         if documents is not None:
#             # Add the parsed documents to the list
#             parsed_pdfs.extend(documents)
#         logger.info(f"Parsed: {str(pdf)}")
#
#     return parsed_pdfs
