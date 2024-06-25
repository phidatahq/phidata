from typing import Iterator, List

from phi.document import Document
from phi.document.reader.arxiv import ArxivReader
from phi.knowledge.base import AssistantKnowledge


class ArxivKnowledgeBase(AssistantKnowledge):
    queries: List[str] = []
    reader: ArxivReader = ArxivReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for _query in self.queries:
            yield self.reader.read(query=_query)
