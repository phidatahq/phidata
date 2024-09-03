from typing import Optional

from phi.tools import Toolkit

try:
    from crawl4ai import WebCrawler
except ImportError:
    raise ImportError(
        "`crawl4ai` not installed. Please install using `pip install crawl4ai @ git+https://github.com/unclecode/crawl4ai.git`"
    )


class Crawl4aiTools(Toolkit):
    def __init__(
        self,
        max_length: Optional[int] = 1000,
    ):
        super().__init__(name="crawl4ai_tools")

        self.max_length = max_length

        self.register(self.web_crawler)

    def web_crawler(self, url: str, max_length: Optional[int] = None) -> str:
        """
        Crawls a website using crawl4ai's WebCrawler.

        :param url: The URL to crawl.
        :param max_length (Optional): The maximum length of the extracted content.

        :return: The results of the crawling.
        """
        if url is None:
            return "No URL provided"

        # Create an instance of WebCrawler
        crawler = WebCrawler(verbose=True)
        crawler.warmup()

        # Run the crawler on a URL
        result = crawler.run(url=url)

        # Determine the length to use
        length = self.max_length or max_length

        # Remove spaces and truncate if length is specified
        if length:
            result = result.markdown[:length]
            result = result.replace(" ", "")
            return result

        result = result.markdown.replace(" ", "")
        return result
