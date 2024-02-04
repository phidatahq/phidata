import json
from pathlib import Path
from typing import List

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger


class JSONReader(Reader):
    """Reader for JSON files"""

    chunk: bool = False

    def read(self, path: Path) -> List[Document]:
        if not path:
            raise ValueError("No path provided")

        if not path.exists():
            raise FileNotFoundError(f"Could not find file: {path}")

        try:
            logger.info(f"Reading: {path}")
            json_name = path.name.split(".")[0]
            json_contents = json.loads(path.read_text("utf-8"))

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
                logger.debug("Chunking documents not yet supported for JSONReader")
                # chunked_documents = []
                # for document in documents:
                #     chunked_documents.extend(self.chunk_document(document))
                # return chunked_documents
            return documents
        except Exception:
            raise
