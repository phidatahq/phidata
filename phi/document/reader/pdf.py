from pathlib import Path
from typing import List, Optional

from phi.document.base import Document
from phi.document.reader.base import ReaderBase
from phi.utils.log import logger


class PdfReader(ReaderBase):
    """Reader for PDF files"""

    path: Path

    def _read(self) -> Optional[List[Document]]:
        try:
            from pypdf import PdfReader  # noqa: F401
        except ImportError:
            raise ImportError("Please install pypdf to load PDF files")

        try:
            self.reader = PdfReader(self.path)
            return [
                Document(
                    content=page.extract_text(),
                    source=str(self.path),
                    meta_data={"page": page_number + 1},
                )
                for page_number, page in enumerate(self.reader.pages)
            ]
        except Exception as e:
            logger.warning(f"Could not read {self.path}: {e}")
            return None


def read_pdfs_from_dir(dir: Path) -> List[Document]:
    """Read data from a PDF and return a list of Documents"""

    logger.info(f"Reading PDFs in: {dir}")
    pdfs_to_read: List[Path] = []
    for pdf in dir.glob("*.pdf"):
        pdfs_to_read.append(pdf)
    logger.info(f"Found {len(pdfs_to_read)} PDFs to read")

    parsed_pdfs: List[Document] = []
    for pdf in pdfs_to_read:
        reader = PdfReader(path=pdf)
        # Parse the PDF document
        documents: Optional[List[Document]] = reader.read()
        if documents is not None:
            # Add the parsed documents to the list
            parsed_pdfs.extend(documents)
        logger.info(f"Parsed: {str(pdf)}")

    return parsed_pdfs
