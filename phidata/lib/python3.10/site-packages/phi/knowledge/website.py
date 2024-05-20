from typing import Iterator, List, Optional

from pydantic import model_validator

from phi.document import Document
from phi.document.reader.website import WebsiteReader
from phi.knowledge.base import AssistantKnowledge
from phi.utils.log import logger


class WebsiteKnowledgeBase(AssistantKnowledge):
    urls: List[str] = []
    reader: Optional[WebsiteReader] = None

    # WebsiteReader parameters
    max_depth: int = 3
    max_links: int = 10

    @model_validator(mode="after")  # type: ignore
    def set_reader(self) -> "WebsiteKnowledgeBase":
        if self.reader is None:
            self.reader = WebsiteReader(max_depth=self.max_depth, max_links=self.max_links)
        return self  # type: ignore

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """
        if self.reader is not None:
            for _url in self.urls:
                yield self.reader.read(url=_url)

    def load(self, recreate: bool = False, upsert: bool = True, skip_existing: bool = True) -> None:
        """Load the website contents to the vector db"""

        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        if self.reader is None:
            logger.warning("No reader provided")
            return

        if recreate:
            logger.debug("Deleting collection")
            self.vector_db.delete()

        logger.debug("Creating collection")
        self.vector_db.create()

        logger.info("Loading knowledge base")
        num_documents = 0

        # Given that the crawler needs to parse the URL before existence can be checked
        # We check if the website url exists in the vector db if recreate is False
        urls_to_read = self.urls.copy()
        if not recreate:
            for url in urls_to_read:
                logger.debug(f"Checking if {url} exists in the vector db")
                if self.vector_db.name_exists(name=url):
                    logger.debug(f"Skipping {url} as it exists in the vector db")
                    urls_to_read.remove(url)

        for url in urls_to_read:
            document_list = self.reader.read(url=url)
            # Filter out documents which already exist in the vector db
            if not recreate:
                document_list = [document for document in document_list if not self.vector_db.doc_exists(document)]

            self.vector_db.insert(documents=document_list)
            num_documents += len(document_list)
            logger.info(f"Loaded {num_documents} documents to knowledge base")

        if self.optimize_on is not None and num_documents > self.optimize_on:
            logger.debug("Optimizing Vector DB")
            self.vector_db.optimize()
