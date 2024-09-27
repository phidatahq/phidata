import csv
from pathlib import Path
from typing import List, Union, IO, Any
from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger
import io


class CSVReader(Reader):
    """Reader for CSV files"""

    def read(self, file: Union[Path, IO[Any]], delimiter: str = ",", quotechar: str = '"') -> List[Document]:
        if not file:
            raise ValueError("No file provided")

        try:
            if isinstance(file, Path):
                if not file.exists():
                    raise FileNotFoundError(f"Could not find file: {file}")
                logger.info(f"Reading: {file}")
                file_content = file.open(newline="", mode="r", encoding="utf-8")
            else:
                logger.info(f"Reading uploaded file: {file.name}")
                file.seek(0)
                file_content = io.StringIO(file.read().decode("utf-8"))

            csv_name = Path(file.name).stem if isinstance(file, Path) else file.name.split(".")[0]
            csv_content = ""
            with file_content as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=delimiter, quotechar=quotechar)
                for row in csv_reader:
                    csv_content += ", ".join(row) + "\n"

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
            logger.error(f"Error reading: {file.name if isinstance(file, IO) else file}: {e}")
            return []
