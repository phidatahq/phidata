from typing import Iterator, List

from phi.document import Document
from phi.document.reader.website import WebsiteReader
from phi.knowledge.base import KnowledgeBase


class WebsiteKnowledgeBase(KnowledgeBase):
    urls: List[str]
    reader: WebsiteReader = WebsiteReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        for _url in self.urls:
            yield self.reader.read(url=_url)
