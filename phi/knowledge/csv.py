from pathlib import Path
from typing import Union, List, Iterator

from phi.document import Document
from phi.document.reader.csv_reader import CSVReader, CSVUrlReader
from phi.knowledge.agent import AgentKnowledge
from phi.utils.log import logger


class CSVKnowledgeBase(AgentKnowledge):
    path: Union[str, Path]
    reader: CSVReader = CSVReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over CSVs and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        _csv_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _csv_path.exists() and _csv_path.is_dir():
            for _csv in _csv_path.glob("**/*.csv"):
                yield self.reader.read(file=_csv)
        elif _csv_path.exists() and _csv_path.is_file() and _csv_path.suffix == ".csv":
            yield self.reader.read(file=_csv_path)


class CSVUrlKnowledgeBase(AgentKnowledge):
    urls: List[str]
    reader: CSVUrlReader = CSVUrlReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        for url in self.urls:
            if url.endswith(".csv"):
                yield self.reader.read(url=url)
            else:
                logger.error(f"Unsupported URL: {url}")
