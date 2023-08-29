import json
from typing import Optional, List

from phi.document import Document
from phi.knowledge.wikipedia import WikiKnowledgeBase
from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class WikiRegistry(FunctionRegistry):
    def __init__(self, knowledge_base: WikiKnowledgeBase):
        super().__init__(name="wiki_registry")
        self.knowledge_base: WikiKnowledgeBase = knowledge_base
        self.register(self.add_wiki_to_knowledge_base)
        self.register(self.search_wiki_knowledge_base)

    def add_wiki_to_knowledge_base(self, topic: str) -> str:
        """Adds information about a topic from wikipedia to the knowledge base.
        Use this function to add information about a topic to the knowledge base if it does not exist.

        :param topic: The topic to add to knowledge base from Wikipedia.
        :return: "Success" if the topic was added to the knowledge base.
        """

        logger.info(f"Adding to knowledge base: {topic}")
        self.knowledge_base.topics = [topic]
        logger.info(f"Loading knowledge base: {topic}")
        self.knowledge_base.load(recreate=False)
        return "Success"

    def search_wiki_knowledge_base(self, query: str) -> str:
        """Searches the Wikipedia knowledge base for a query.

        :param query: The query to search for.
        :return: Relevant documents from wikipedia knowledge base.
        """
        logger.info(f"Searching website for: {query}")
        relevant_docs: List[Document] = self.knowledge_base.search(query=query)
        return json.dumps([doc.to_dict() for doc in relevant_docs])
