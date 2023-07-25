from typing import List, Iterator

from phi.document import Document
from phi.llm.knowledge.base import LLMKnowledgeBase


class CombinedKnowledgeBase(LLMKnowledgeBase):
    sources: List[LLMKnowledgeBase]

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
