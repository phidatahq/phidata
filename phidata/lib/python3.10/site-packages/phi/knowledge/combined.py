from typing import List, Iterator

from phi.document import Document
from phi.knowledge.base import AssistantKnowledge
from phi.utils.log import logger


class CombinedKnowledgeBase(AssistantKnowledge):
    sources: List[AssistantKnowledge] = []

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over knowledge bases and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for kb in self.sources:
            logger.debug(f"Loading documents from {kb.__class__.__name__}")
            yield from kb.document_lists
