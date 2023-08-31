import json
from typing import List, Optional

from phi.document import Document
from phi.knowledge.wikipedia import WikiKnowledgeBase
from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class WikiRegistry(FunctionRegistry):
    def __init__(self, knowledge_base: Optional[WikiKnowledgeBase] = None):
        super().__init__(name="wiki_registry")
        self.knowledge_base: Optional[WikiKnowledgeBase] = knowledge_base
        if self.knowledge_base is not None:
            self.register(self.add_wikipedia_articles_to_knowledge_base)
            self.register(self.search_wikipedia_knowledge_base)
        else:
            self.register(self.search_wikipedia)

    def add_wikipedia_articles_to_knowledge_base(self, topic: str) -> str:
        """Adds information about a topic from wikipedia to the knowledge base.
        Use this function to add information about a topic to the knowledge base if it does not exist.

        :param topic: The topic to add to knowledge base from Wikipedia.
        :return: "Success" if information about the topic was successfully added to the knowledge base.
        """
        if self.knowledge_base is None:
            return "Knowledge base not provided"

        logger.info(f"Adding to knowledge base: {topic}")
        self.knowledge_base.topics.append(topic)
        logger.info(f"Loading knowledge base: {topic}")
        self.knowledge_base.load(recreate=False)
        return "Success"

    def search_wikipedia_knowledge_base(self, query: str) -> str:
        """Searches the Wikipedia knowledge base for a query.

        :param query: The query to search for.
        :return: Relevant documents from wikipedia knowledge base.
        """
        if self.knowledge_base is None:
            return "Knowledge base not provided"

        logger.info(f"Searching wikipedia for: {query}")
        relevant_docs: List[Document] = self.knowledge_base.search(query=query)
        return json.dumps([doc.to_dict() for doc in relevant_docs])

    def search_wikipedia(self, query: str) -> str:
        """Searches Wikipedia for a query.

        :param query: The query to search for.
        :return: Relevant documents from wikipedia.
        """
        try:
            import wikipedia  # noqa: F401
        except ImportError:
            raise ImportError(
                "The `wikipedia` package is not installed. " "Please install it via `pip install wikipedia`."
            )

        logger.info(f"Searching wikipedia for: {query}")
        return json.dumps(Document(name=query, content=wikipedia.summary(query)).to_dict())
