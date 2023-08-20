import json
from pathlib import Path
from typing import List

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger


class WebsiteReader(Reader):
    """Reader for JSON files"""

    chunk: bool = False

    def read(self, url: str) -> List[Document]:
        return []
        # ABC: Implement website reader
        # if not url:
        #     raise ValueError("No url provided")
        #
        # if not url.exists():
        #     raise FileNotFoundError(f"Could not find file: {url}")
        #
        # try:
        #     logger.info(f"Reading: {url}")
        #     json_name = url.name.split(".")[0]
        #     json_contents = json.loads(url.read_text("utf-8"))
        #
        #     if isinstance(json_contents, dict):
        #         json_contents = [json_contents]
        #
        #     documents = [
        #         Document(
        #             name=json_name,
        #             meta_data={"page": page_number},
        #             content=json.dumps(content),
        #         )
        #         for page_number, content in enumerate(json_contents, start=1)
        #     ]
        #     if self.chunk:
        #         logger.debug("Chunking documents not yet supported for JSONReader")
        #         # chunked_documents = []
        #         # for document in documents:
        #         #     chunked_documents.extend(self.chunk_document(document))
        #         # return chunked_documents
        #     return documents
        # except Exception:
        #     raise
