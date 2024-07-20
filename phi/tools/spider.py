import json

try:
    from spider import Spider as ExternalSpider
except ImportError:
    raise ImportError("`spider-client` not installed. Please install using `pip install spider-client`")

from spider import Spider as ExternalSpider  # type: ignore
from typing import Optional

from phi.tools.toolkit import Toolkit
from phi.utils.log import logger


class Spider(Toolkit):
    def __init__(
        self,
        max_results: Optional[int] = None,
    ):
        super().__init__(name="spider")
        self.max_results = max_results
        self.register(self.search)

    def search(self, query: str, max_results: int = 5) -> str:
        """Use this function to search the web.
        Args:
            query (str): The query to search the web with.
            max_results (int, optional): The maximum number of results to return. Defaults to 5.
        Returns:
            The results of the search.
        """
        max_results = self.max_results or max_results
        return self._search(query, max_results=max_results)

    def _search(self, query: str, max_results: int = 1) -> str:
        app = ExternalSpider()
        logger.info(f"Fetching results from spider for query: {query} with max_results: {max_results}")
        try:
            options = {"fetch_page_content": False, "num": max_results}
            results = app.search(query, options)
            return json.dumps(results)
        except Exception as e:
            logger.error(f"Error fetching results from spider: {e}")
            return f"Error fetching results from spider: {e}"
