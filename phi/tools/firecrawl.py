import json
from typing import Optional, List
import os
import time
from phi.utils.log import logger


from phi.tools import Toolkit

try:
    from firecrawl import FirecrawlApp
except ImportError:
    raise ImportError("`firecrawl-py` not installed. Please install using `pip install firecrawl-py`")


# TODO: Segregate `limit` param into `crawl_limit` and `map_limit` since both serve different purposes
class FirecrawlTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        formats: Optional[List[str]] = None,
        limit: int = 10,
        scrape: bool = True,
        crawl: bool = False,
        async_crawl: bool = False,
        map: bool = False,
    ):
        super().__init__(name="firecrawl_tools")

        self.api_key: Optional[str] = api_key or os.getenv("FIRECRAWL_API_KEY")
        if self.api_key is None:
            raise ValueError(
                "No API key provided. Please set the FIRECRAWL_API_KEY environment variable or pass it as an argument."
            )

        self.api_url: Optional[str] = api_url or os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev")
        self.formats: Optional[List[str]] = formats
        self.limit: int = limit
        self.app: FirecrawlApp = FirecrawlApp(api_key=self.api_key)

        if scrape:
            self.register(self.scrape_website)
        if crawl:
            self.register(self.crawl_website)
        if async_crawl:
            self.register(self.async_crawl_website)
        if crawl or async_crawl:
            self.register(self.check_crawl_status)
            self.register(self.cancel_crawl)
        if map:
            self.register(self.map_website)

    def scrape_website(self, url: str) -> str:
        """Use this function to scrape the given website using Firecrawl.

        Args:
            url (str): The URL to scrape.

        Returns:
            The results of the scraping.
        """
        if url is None:
            raise ValueError("No URL provided. URL is required for scraping.")

        params = {}
        if self.formats:
            if set(self.formats).issubset(
                set(["markdown", "html", "rawHtml", "links", "screenshot", "extract", "screenshot@fullPage"])
            ):
                params["formats"] = self.formats
            else:
                raise ValueError(
                    "Invalid formats provided for scraping. Valid formats are: markdown, html, rawHtml, links, screenshot, extract, screenshot@fullPage"
                )
        scrape_result = self.app.scrape_url(url, params=params)
        return json.dumps(scrape_result)

    def crawl_website(self, url: str, limit: Optional[int]) -> str:
        """Use this function to Crawl a website using Firecrawl.

        Args:
            url (str): The URL to crawl.
            limit (int): The maximum number of pages to crawl

        Returns:
            str: The results of the crawling.
        """
        if url is None:
            raise ValueError("No URL provided. URL is required for crawling.")

        params = {}
        if self.limit or limit:
            params["limit"] = self.limit or limit
            if self.formats and set(self.formats).issubset(set(["markdown", "html", "rawHtml", "links", "screenshot"])):
                params["scrapeOptions"] = {"formats": self.formats}  # type: ignore

        crawl_result = self.app.crawl_url(url, params=params, poll_interval=15)
        return json.dumps(crawl_result)

    def async_crawl_website(self, url: str, limit: Optional[int]) -> str:
        """Use this function to Asynchronously crawl a website using Firecrawl.

        Args:
            url (str): The URL to crawl.
            limit (int): The maximum number of pages to crawl.

        Returns:
            str: The crawl results in JSON format.
        """
        if url is None:
            raise ValueError("No URL provided. URL is required for crawling.")

        params = {}
        logger.info("`limit` parameter will be deprecated in future release with `crawl_limit` parameter.")
        if self.limit or limit:
            params["limit"] = self.limit or limit
            if self.formats and set(self.formats).issubset(set(["markdown", "html", "rawHtml", "links", "screenshot"])):
                params["scrapeOptions"] = {"formats": self.formats} # type: ignore
        poll_interval: int = 15

        # Firecrawl async_crawl_url returns crawl job id, hence adding custom implementation  with helper functions to return final  async crawl response.
        try:
            initial_status = self.app.async_crawl_url(url, params=params)
            crawl_id = initial_status.get("id")

            if not crawl_id:
                raise ValueError("No crawl ID received from async crawl initiation")

            # Monitor the crawl until completion
            while True:
                status_response = self.app.check_crawl_status(crawl_id)
                current_status = status_response.get("status")

                if current_status == "completed":
                    if "data" in status_response:
                        return json.dumps(status_response)
                    else:
                        raise ValueError("Crawl completed but no data was returned")

                elif current_status in ["active", "paused", "pending", "queued", "waiting", "scraping"]:
                    time.sleep(max(poll_interval, 2))

                else:
                    raise ValueError(f"Crawl failed or was stopped. Status: {current_status}")

        except Exception as e:
            return json.dumps({"error": str(e)})

    def check_crawl_status(self, crawl_id: str) -> str:
        """Use this function to Check the status of a crawl job.

        Args:
            crawl_id (str): The ID of the crawl job to check.

        Returns:
            str: The current status of the crawl job in JSON format.
        """
        if not crawl_id:
            raise ValueError("No crawl ID provided. Crawl ID is required to check a crawl status.")

        response = self.app.check_crawl_status(crawl_id)
        return json.dumps(response)

    def cancel_crawl(self, crawl_id: str) -> str:
        """Use this function to Cancel an ongoing crawl job.

        Args:
            crawl_id (str): The ID of the crawl job to cancel.

        Returns:
            str: The cancellation status in JSON format.
        """
        if not crawl_id:
            raise ValueError("No crawl ID provided. Crawl ID is required to cancel a crawl.")

        cancel_status = self.app.cancel_crawl(crawl_id)
        return json.dumps(cancel_status)

    def map_website(
        self, url: str, include_subdomains: bool = False, ignore_sitemap: bool = True, limit: Optional[int] = 10
    ) -> str:
        """Use this function to Generate a list of URLs( map search ) from a website.

        Args:
            url (str): The URL of the website to map.
            include_subdomains (bool): Include subdomains of the website. Defaults to False.
            ignore_sitemap (bool): Ignore the website sitemap when crawling. Defaults to True.
            limit (int): The maximum number of links to map. Defaults to 10.

        Returns:
            str: The mapping results in JSON format.
        """
        if url is None:
            raise ValueError("No URL provided. URL is required for mapping.")

        params = dict()
        logger.info("`limit` parameter will be deprecated in future release with `map_limit` parameter.")
        if self.limit or limit:
            params["limit"] = self.limit or limit

        params.update({"includeSubdomains": include_subdomains, "ignoreSitemap": ignore_sitemap})

        map_result = self.app.map_url(url, params=params)
        return json.dumps(map_result)
