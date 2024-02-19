import json
from typing import Any, Optional

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from duckduckgo_search import DDGS
except ImportError:
    logger.warning("`duckduckgo-search` not installed.")


class DuckDuckGo(Toolkit):
    def __init__(
        self,
        ddgs: Optional[Any] = None,
        headers: Optional[Any] = None,
        proxies: Optional[Any] = None,
        timeout: Optional[int] = 10,
    ):
        super().__init__(name="duckduckgo")

        self.ddgs = ddgs or DDGS(headers=headers, proxies=proxies, timeout=timeout)
        self.register(self.duckduckgo_search)
        self.register(self.duckduckgo_news)

    def duckduckgo_search(self, query: str, max_results: Optional[int] = 5) -> str:
        """Use this function to search DuckDuckGo for a query.

        Args:
            query(str): The query to search for.
            max_results (optional, default=5): The maximum number of results to return.

        Returns:
            The result from DuckDuckGo.
        """
        logger.debug(f"Searching DDG for: {query}")
        results = [r for r in self.ddgs.text(keywords=query, max_results=max_results)]
        return json.dumps(results, indent=2)

    def duckduckgo_news(self, query: str, max_results: Optional[int] = 5) -> str:
        """Use this function to get the latest news from DuckDuckGo.

        Args:
            query(str): The query to search for.
            max_results (optional, default=5): The maximum number of results to return.

        Returns:
            The latest news from DuckDuckGo.
        """
        logger.debug(f"Searching DDG news for: {query}")
        results = [r for r in self.ddgs.news(keywords=query, max_results=max_results)]
        return json.dumps(results, indent=2)
