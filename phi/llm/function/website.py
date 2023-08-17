from phi.llm.function.registry import FunctionRegistry
from phi.knowledge import KnowledgeBase
from phi.utils.log import logger


class WebsiteRegistry(FunctionRegistry):
    def __init__(self, knowledge_base: KnowledgeBase):
        super().__init__(name="website_registry")
        self.knowledge_base: KnowledgeBase = knowledge_base
        self.register(self.add_website_to_knowledge_base)
        self.register(self.search_website_knowledge_base)

    def add_website_to_knowledge_base(self, url: str) -> str:
        """Adds the content of a website to the knowledge base.

        :param url: The url of the website to add.
        :return: The result from Google.
        """
        logger.info(f"Parsing website: {url}")
        return "Sorry, this capability is not available yet."

    def search_website_knowledge_base(self, query: str) -> str:
        """Searches the website's knowledge base for a query.

        :param query: The query to search for.
        :return: The result from Google.
        """
        logger.info(f"Searching website for: {query}")
        return "Sorry, this capability is not available yet."
