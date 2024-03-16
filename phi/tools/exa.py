from os import getenv
from typing import Optional

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from exa_py import Exa
except ImportError:
    raise ImportError("`exa_py` not installed. Please install using `pip install exa_py`.")

def process_exa_results(results):
    links = [result.url for result in results.results]
    return "\n".join(links)

class ExaTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        super().__init__(name="exa")

        self.api_key = api_key or getenv("EXA_API_KEY")
        if not self.api_key:
            logger.error("No Exa API key provided")

        self.register(self.search_exa)

    def search_exa(self, query: str) -> str:
        """Searches Exa for a query.

        :param query: The query to search for.
        :return: Relevant documents from exa.
        """
        if not self.api_key:
            return "Please provide an API key"

        logger.info(f"Searching exa for: {query}")

        exa = Exa(self.api_key)

        try:
            return process_exa_results(exa.search(query))
        except Exception as e:
            logger.error(f"Failed to search exa {e}")
            return f"Error: {e}"
