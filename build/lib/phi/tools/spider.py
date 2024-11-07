import json

try:
    from spider import Spider as ExternalSpider
except ImportError:
    raise ImportError("`spider-client` not installed. Please install using `pip install spider-client`")

from typing import Optional

from phi.tools.toolkit import Toolkit
from phi.utils.log import logger


class SpiderTools(Toolkit):
    def __init__(
        self,
        max_results: Optional[int] = None,
        url: Optional[str] = None,
    ):
        super().__init__(name="spider")
        self.max_results = max_results
        self.url = url
        self.register(self.search)
        self.register(self.scrape)
        self.register(self.crawl)

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

    def scrape(self, url: str) -> str:
        """Use this function to scrape the content of a webpage.
        Args:
            url (str): The URL of the webpage to scrape.
        Returns:
            Markdown of the webpage.
        """
        return self._scrape(url)

    def crawl(self, url: str) -> str:
        """Use this function to crawl a webpage.
        Args:
            url (str): The URL of the webpage to crawl.
        Returns:
            Markdown of all the pages on the URL.
        """
        return self._crawl(url)

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

    def _scrape(self, url: str) -> str:
        app = ExternalSpider()
        logger.info(f"Fetching content from spider for url: {url}")
        try:
            options = {"return_format": "markdown"}
            results = app.scrape_url(url, options)
            return json.dumps(results)
        except Exception as e:
            logger.error(f"Error fetching content from spider: {e}")
            return f"Error fetching content from spider: {e}"

    def _crawl(self, url: str) -> str:
        app = ExternalSpider()
        logger.info(f"Fetching content from spider for url: {url}")
        try:
            options = {"return_format": "markdown"}
            results = app.crawl_url(url, options)
            return json.dumps(results)
        except Exception as e:
            logger.error(f"Error fetching content from spider: {e}")
            return f"Error fetching content from spider: {e}"
