from typing import Optional, Dict, Any, List
from phi.tools import Toolkit

try:
    from firecrawl import FirecrawlApp
except ImportError:
    raise ImportError(
        "`firecrawl` not installed. Please install using `pip install firecrawl`"
    )

class FirecrawlTools(Toolkit):
    def __init__(
        self,
        api_key: str,
        max_length: Optional[int] = None,
    ):
        super().__init__(name="firecrawl_tools")

        self.api_key = api_key
        self.max_length = max_length
        self.app = FirecrawlApp(api_key=self.api_key)

        self.register(self.scrape_or_crawl_website)

    def scrape_or_crawl_website(self, url: str, method: str = "scrape", limit: int = 10, formats: str = "", max_length: Optional[int] = None) -> str:
        """
        Scrapes or crawls a website using Firecrawl's methods.

        :param url: The URL to scrape or crawl.
        :param method: The method to use, either "scrape" or "crawl".
        :param limit: The maximum number of pages to crawl (only used for crawl method).
        :param formats: Comma-separated list of formats to return (e.g., "markdown,html").
        :param max_length: The maximum length of the extracted content.

        :return: The results of the scraping or crawling.
        """
        if url is None:
            return "No URL provided"

        params = {}
        if formats:
            params['formats'] = formats.split(',')

        if method.lower() == "crawl":
            params['limit'] = limit
            params['scrapeOptions'] = params.copy()
            status = self.app.crawl_url(
                url,
                params=params,
                wait_until_done=True,
                poll_interval=30
            )
        else:  # default to scrape
            status = self.app.scrape_url(url, params=params)

        # Assuming the status contains the scraped/crawled content
        result = str(status)  # Convert to string, adjust based on actual return type

        # Determine the length to use
        length = self.max_length or max_length

        # Truncate if length is specified
        if length:
            result = result[:length]

        return result
