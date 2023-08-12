from typing import List, Iterator

from phi.document import Document
from phi.knowledge.base import KnowledgeBase


class CombinedKnowledgeBase(KnowledgeBase):
    sources: List[KnowledgeBase]

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over knowledge bases and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for kb in self.sources:
            for document_list in kb.document_lists:
                yield document_list
