from phi.tools import Toolkit
from phi.utils.log import logger


class GoogleTools(Toolkit):
    def __init__(self):
        super().__init__(name="google_tools")

        self.register(self.get_result_from_google)

    def get_result_from_google(self, query: str) -> str:
        """Gets the result for a query from Google.
        Use this function to find an answer when not available in the knowledge base.

        :param query: The query to search for.
        :return: The result from Google.
        """
        logger.info(f"Searching google for: {query}")
        return "Sorry, this capability is not available yet."
