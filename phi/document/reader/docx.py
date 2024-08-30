from pathlib import Path
from typing import List, Union
from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger
import io

class DocxReader(Reader):
    """Reader for Doc/Docx files"""

    def read(self, file: Union[Path, io.BytesIO]) -> List[Document]:
        if not file:
            raise ValueError("No file provided")

        try:
            import textract  # noqa: F401
        except ImportError:
            raise ImportError("`textract` not installed")

        try:
            if isinstance(file, Path):
                logger.info(f"Reading: {file}")
                doc_content = textract.process(file)
                doc_name = file.stem
            else:  # Handle file-like object from upload
                logger.info(f"Reading uploaded file: {file.name}")
                doc_content = textract.process(file.read())
                doc_name = file.name.split(".")[0]

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
            logger.error(f"Error reading file: {e}")
            return []