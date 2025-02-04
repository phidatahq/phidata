import json
from io import BytesIO
from pathlib import Path
from typing import List, Union

from agno.document.base import Document
from agno.document.reader.base import Reader
from agno.utils.log import logger


class JSONReader(Reader):
    """Reader for JSON files"""

    chunk: bool = False

    def read(self, file: Union[Path, BytesIO]) -> List[Document]:
        try:
            if isinstance(file, Path):
                if not file.exists():
                    raise FileNotFoundError(f"Could not find file: {file}")
                logger.info(f"Reading: {file}")
                json_name = file.name.split(".")[0]
                json_contents = json.loads(file.read_text("utf-8"))

            elif isinstance(file, BytesIO):
                logger.info("Reading file from BytesIO stream")
                json_name = file.name.split(".")[0]
                file.seek(0)
                json_contents = json.load(file)

            else:
                raise ValueError("Unsupported file type. Must be Path or BytesIO.")

            if isinstance(json_contents, dict):
                json_contents = [json_contents]

            documents = [
                Document(
                    name=json_name,
                    id=f"{json_name}_{page_number}",
                    meta_data={"page": page_number},
                    content=json.dumps(content),
                )
                for page_number, content in enumerate(json_contents, start=1)
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document))
                return chunked_documents
            return documents
        except Exception:
            raise
