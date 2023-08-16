from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class PubMedRegistry(FunctionRegistry):
    def __init__(self):
        super().__init__(name="pubmed_registry")
        self.register(self.get_articles_from_pubmed)

    def get_articles_from_pubmed(self, query: str, num_articles: int = 2) -> str:
        """Gets the abstract for articles related to a query from PubMed: a database of biomedical literature
        Use this function to find information about a medical concept when not available in the knowledge base or Google

        :param query: The query to get related articles for.
        :param num_articles: The number of articles to return.
        :return: JSON string containing the articles
        """
        logger.info(f"Searching Pubmed for: {query}")
        return "Sorry, this capability is not available yet."
