from os import getenv
from typing import List, Optional

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from apify_client import ApifyClient
except ImportError:
    raise ImportError("`apify_client` not installed. Please install using `pip install apify-client`")


class ApifyTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        website_content_crawler: bool = True,
        web_scraper: bool = False,
    ):
        super().__init__(name="apify_tools")

        self.api_key = api_key or getenv("MY_APIFY_TOKEN")
        if not self.api_key:
            logger.error("No Apify API key provided")

        self.register(self.website_content_crawler)
        if web_scraper:
            self.register(self.web_scrapper)

    def website_content_crawler(self, urls: List[str], timeout: Optional[int] = 60) -> str:
        if self.api_key is None:
            return "No API key provided"

        if urls is None:
            return "No URLs provided"

        client = ApifyClient(self.api_key)

        logger.debug(f"Crawling URLs: {urls}")

        formatted_urls = [{"url": url} for url in urls]

        run_input = {"startUrls": formatted_urls}

        run = client.actor("apify/website-content-crawler").call(run_input=run_input, timeout_secs=timeout)

        results: str = ""

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results += "Results for URL: " + item.get("url") + "\n"
            results += item.get("text") + "\n"

        return results

    def web_scrapper(self, urls: List[str], timeout: Optional[int] = 60) -> str:
        """
        Scrapes a website using Apify's web-scraper actor.

        :param urls: The URLs to scrape.
        :param timeout: The timeout for the scraping.

        :return: The results of the scraping.
        """
        if self.api_key is None:
            return "No API key provided"

        if urls is None:
            return "No URLs provided"

        client = ApifyClient(self.api_key)

        logger.debug(f"Scrapping URLs: {urls}")

        formatted_urls = [{"url": url} for url in urls]

        run_input = {
            "pageFunction": "// The function accepts a single argument: the \"context\" object.\n// For a complete list of its properties and functions,\n// see https://apify.com/apify/web-scraper#page-function \nasync function pageFunction(context) {\n    // This statement works as a breakpoint when you're trying to debug your code. Works only with Run mode: DEVELOPMENT!\n    // debugger; \n\n    // jQuery is handy for finding DOM elements and extracting data from them.\n    // To use it, make sure to enable the \"Inject jQuery\" option.\n    const $ = context.jQuery;\n    const pageTitle = $('title').first().text();\n    const h1 = $('h1').first().text();\n    const first_h2 = $('h2').first().text();\n    const random_text_from_the_page = $('p').first().text();\n\n\n    // Print some information to actor log\n    context.log.info(`URL: ${context.request.url}, TITLE: ${pageTitle}`);\n\n    // Manually add a new page to the queue for scraping.\n   await context.enqueueRequest({ url: 'http://www.example.com' });\n\n    // Return an object with the data extracted from the page.\n    // It will be stored to the resulting dataset.\n    return {\n        url: context.request.url,\n        pageTitle,\n        h1,\n        first_h2,\n        random_text_from_the_page\n    };\n}",
            "startUrls": formatted_urls,
        }

        run = client.actor("apify/web-scraper").call(run_input=run_input, timeout_secs=timeout)

        results: str = ""

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results += "Results for URL: " + item.get("url") + "\n"
            results += item.get("pageTitle") + "\n"
            results += item.get("h1") + "\n"
            results += item.get("first_h2") + "\n"
            results += item.get("random_text_from_the_page") + "\n"

        return results
