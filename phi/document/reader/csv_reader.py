import csv
from pathlib import Path
from typing import List

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger


class CSVReader(Reader):
    """Reader for CSV files"""

    def read(self, path: Path, delimiter: str = " ", quotechar: str = "|") -> List[Document]:
        if not path:
            raise ValueError("No path provided")

        if not path.exists():
            raise FileNotFoundError(f"Could not find file: {path}")

        try:
            logger.info(f"Reading: {path}")
            csv_name = path.name.split("/")[-1].split(".")[0].replace("/", "_").replace(" ", "_")
            csv_content = ""
            with open(path, newline="") as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=delimiter, quotechar=quotechar)
                for row in csv_reader:
                    csv_content += ", ".join(row)
            documents = [
                Document(
                    name=csv_name,
                    id=csv_name,
                    content=csv_content,
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
