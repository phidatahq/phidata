from pathlib import Path
from typing import List

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger


class TextReader(Reader):
    """Reader for Text files"""

    def read(self, path: Path) -> List[Document]:
        if not path:
            raise ValueError("No path provided")

        if not path.exists():
            raise FileNotFoundError(f"Could not find file: {path}")

        try:
            logger.info(f"Reading: {path}")
            file_name = path.name.split("/")[-1].split(".")[0].replace("/", "_").replace(" ", "_")
            file_contents = path.read_text()
            documents = [
                Document(
                    name=file_name,
                    id=file_name,
                    content=file_contents,
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
