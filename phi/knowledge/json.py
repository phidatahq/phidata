from pathlib import Path
from typing import Union, List, Iterator

from phi.document import Document
from phi.document.reader.json import JSONReader
from phi.knowledge.base import AssistantKnowledge


class JSONKnowledgeBase(AssistantKnowledge):
    path: Union[str, Path]
    reader: JSONReader = JSONReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over Json files and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        _json_path: Path = Path(self.path) if isinstance(self.path, str) else self.path

        if _json_path.exists() and _json_path.is_dir():
            for _pdf in _json_path.glob("*.json"):
                yield self.reader.read(path=_pdf)
        elif _json_path.exists() and _json_path.is_file() and _json_path.suffix == ".json":
            yield self.reader.read(path=_json_path)
