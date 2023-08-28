from typing import Iterator, List

from phi.document import Document
from phi.knowledge.base import KnowledgeBase
import wikipedia
from phi.utils.log import logger



class WikiKnowledgeBase(KnowledgeBase):
    topics: List[str]

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for topic in self.topics:
            yield [Document(
                name=topic,
                meta_data={"topic": topic},
                content=wikipedia.summary(topic),
            )]
