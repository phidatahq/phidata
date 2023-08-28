import json
from typing import List

from phi.document import Document
from phi.knowledge.arxiv import ArxivKnowledgeBase
from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class ArxivRegistry(FunctionRegistry):
    def __init__(self, knowledge_base: ArxivKnowledgeBase):
        super().__init__(name="arxiv_registry")
        self.knowledge_base: ArxivKnowledgeBase = knowledge_base
        # self.register(self.add_website_to_knowledge_base)
        self.register(self.search_arxiv_knowledge_base)

    def add_arxiv_to_knowledge_base(self, url: str) -> str:
        """Adds the content of a website to the knowledge base.

        :param url: The url of the website to add.
        :return: The result from Google.
        """

        logger.info(f"Adding to knowledge base: {url}")
        self.knowledge_base.urls = [url]
        self.knowledge_base.load(recreate=False)
        return "done."

    def search_arxiv_knowledge_base(self, query: str) -> str:
        """Searches the Arxiv's knowledge base for a query.

        :param query: The query to search for.
        :return: The result from Google.
        """
        logger.info(f"Searching arxiv for: {query}")
        relevant_docs: List[Document] = self.knowledge_base.search(query=query)
        return json.dumps([doc.to_dict() for doc in relevant_docs])
