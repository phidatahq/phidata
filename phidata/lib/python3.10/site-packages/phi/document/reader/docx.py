from pathlib import Path
from typing import List

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger


class DocxReader(Reader):
    """Reader for Doc/Docx files"""

    def read(self, path: Path) -> List[Document]:
        if not path:
            raise ValueError("No path provided")

        if not path.exists():
            raise FileNotFoundError(f"Could not find file: {path}")

        try:
            import textract  # noqa: F401
        except ImportError:
            raise ImportError("`textract` not installed")

        try:
            logger.info(f"Reading: {path}")
            doc_name = path.name.split("/")[-1].split(".")[0].replace("/", "_").replace(" ", "_")
            doc_content = textract.process(path)
            documents = [
                Document(
                    name=doc_name,
                    id=doc_name,
                    content=doc_content.decode("utf-8"),
                )
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document))
                return chunked_documents
            return documents
        except Exception as e:
            logger.error(f"Error reading: {path}: {e}")
        return []
