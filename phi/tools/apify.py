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
        urls: Optional[List[str]] = None,
        web_scraper: bool = True,
    ):
        super().__init__(name="apify_tools")

        self.api_key = api_key or getenv("MY_APIFY_TOKEN")
        if not self.api_key:
            logger.error("No Apify API key provided")

        self.urls = urls

        if web_scraper:
            self.register(self.web_scrapper)

    def web_scrapper(
        self, _urls: Optional[str], _crawling_depth: Optional[int], _max_pages_per_crawl: Optional[int]
    ) -> str:
        """
        Scrapes a website using Apify's web-scraper actor.

        :param urls: The urls to scrape.
        :param crawling_depth: The depth to crawl.
        :param max_pages_per_crawl: The maximum number of pages to crawl.
        :return: The results of the scraping.
        """
        client = ApifyClient(self.api_key)

        if self.urls is None and _urls is None:
            return "No URLs provided"

        combined_urls: List = []

        if self.urls and _urls:
            combined_urls = self.urls
            combined_urls.append(_urls)
        elif self.urls:
            combined_urls = self.urls
        elif _urls:
            combined_urls.append(_urls)

        logger.debug(f"Scrapping URLs: {combined_urls}")

        formatted_urls = [{"url": url} for url in combined_urls]

        input = {
            "breakpointLocation": "NONE",
            "browserLog": False,
            "closeCookieModals": False,
            "debugLog": False,
            "downloadCss": True,
            "downloadMedia": True,
            "headless": True,
            "ignoreCorsAndCsp": False,
            "ignoreSslErrors": False,
            "injectJQuery": True,
            "keepUrlFragments": False,
            "linkSelector": "a[href]",
            "maxCrawlingDepth": _crawling_depth or 2,
            "maxPagesPerCrawl": _max_pages_per_crawl or 5,
            "pageFunction": "// The function accepts a single argument: the \"context\" object.\n// For a complete list of its properties and functions,\n// see https://apify.com/apify/web-scraper#page-function \nasync function pageFunction(context) {\n    // This statement works as a breakpoint when you're trying to debug your code. Works only with Run mode: DEVELOPMENT!\n    // debugger; \n\n    // jQuery is handy for finding DOM elements and extracting data from them.\n    // To use it, make sure to enable the \"Inject jQuery\" option.\n    const $ = context.jQuery;\n    const pageTitle = $('title').first().text();\n    const h1 = $('h1').first().text();\n    const first_h2 = $('h2').first().text();\n    const random_text_from_the_page = $('p').first().text();\n\n\n    // Print some information to actor log\n    context.log.info(`URL: ${context.request.url}, TITLE: ${pageTitle}`);\n\n    // Manually add a new page to the queue for scraping.\n   await context.enqueueRequest({ url: 'http://www.example.com' });\n\n    // Return an object with the data extracted from the page.\n    // It will be stored to the resulting dataset.\n    return {\n        url: context.request.url,\n        pageTitle,\n        h1,\n        first_h2,\n        random_text_from_the_page\n    };\n}",
            "postNavigationHooks": '// We need to return array of (possibly async) functions here.\n// The functions accept a single argument: the "crawlingContext" object.\n[\n    async (crawlingContext) => {\n        // ...\n    },\n]',
            "preNavigationHooks": '// We need to return array of (possibly async) functions here.\n// The functions accept two arguments: the "crawlingContext" object\n// and "gotoOptions".\n[\n    async (crawlingContext, gotoOptions) => {\n        // ...\n    },\n]\n',
            "proxyConfiguration": {"useApifyProxy": True},
            "runMode": "DEVELOPMENT",
            "startUrls": formatted_urls,
            "useChrome": False,
            "waitUntil": ["networkidle2"],
        }

        run = client.actor("apify/web-scraper").call(run_input=input)

        results: str = ""

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results += item.get("url") + "\n"
            results += item.get("pageTitle") + "\n"
            results += item.get("h1") + "\n"
            results += item.get("first_h2") + "\n"
            results += item.get("random_text_from_the_page") + "\n"

        return results
