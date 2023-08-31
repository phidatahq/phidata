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
        self.register(self.add_arxiv_articles_to_knowledge_base)
        self.register(self.search_arxiv_knowledge_base)

    def add_arxiv_articles_to_knowledge_base(self, topic: str) -> str:
        """This function adds articles about a topic from arXiv to the knowledge base.
        arXiv is an open-access archive for scholarly articles.
        Use this function to add articles about a topic to the knowledge base if it does not exist.

        :param topic: The topic to add to knowledge base from arXiv.
        :return: "Success" if information about the topic was successfully added to the knowledge base.
        """

        logger.info(f"Adding to knowledge base: {topic}")
        self.knowledge_base.queries.append(topic)
        logger.info(f"Loading knowledge base: {topic}")
        self.knowledge_base.load(recreate=False)
        return "Success"

    def search_arxiv_knowledge_base(self, query: str) -> str:
        """Search the arXiv knowledge base for a query.

        :param query: The query to search for.
        :return: The result from arXiv knowledge base.
        """
        logger.info(f"Searching arxiv for: {query}")
        relevant_docs: List[Document] = self.knowledge_base.search(query=query)
        return json.dumps([doc.to_dict() for doc in relevant_docs])
