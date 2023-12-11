import json
from typing import List, Optional

from phi.document import Document
from phi.knowledge.arxiv import ArxivKnowledgeBase
from phi.tools import ToolRegistry
from phi.utils.log import logger


class ArxivTools(ToolRegistry):
    def __init__(self, knowledge_base: Optional[ArxivKnowledgeBase] = None):
        super().__init__(name="arxiv_tools")

        self.knowledge_base: Optional[ArxivKnowledgeBase] = knowledge_base

        if self.knowledge_base is not None and isinstance(self.knowledge_base, ArxivKnowledgeBase):
            self.register(self.search_arxiv_and_update_knowledge_base)
        else:
            self.register(self.search_arxiv)

    def search_arxiv_and_update_knowledge_base(self, topic: str) -> str:
        """This function searches arXiv for a topic, adds the results to the knowledge base and returns them.

        USE THIS FUNCTION TO GET INFORMATION WHICH DOES NOT EXIST.

        :param topic: The topic to search arXiv and add to knowledge base.
        :return: Relevant documents from arXiv knowledge base.
        """
        if self.knowledge_base is None:
            return "Knowledge base not provided"

        logger.debug(f"Adding to knowledge base: {topic}")
        self.knowledge_base.queries.append(topic)
        logger.debug("Loading knowledge base.")
        self.knowledge_base.load(recreate=False)
        logger.debug(f"Searching knowledge base: {topic}")
        relevant_docs: List[Document] = self.knowledge_base.search(query=topic)
        return json.dumps([doc.to_dict() for doc in relevant_docs])

    def search_arxiv(self, query: str, max_results: int = 5) -> str:
        """
        Searches arXiv for a query.

        :param query: The query to search for.
        :param max_results: The maximum number of results to return.
        :return: Relevant documents from arXiv.
        """
        from phi.document.reader.arxiv import ArxivReader

        arxiv = ArxivReader(max_results=max_results)

        logger.debug(f"Searching arxiv for: {query}")
        relevant_docs: List[Document] = arxiv.read(query=query)
        return json.dumps([doc.to_dict() for doc in relevant_docs])
