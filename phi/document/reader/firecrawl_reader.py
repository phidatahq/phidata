from typing import Dict, List, Optional, Literal

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.utils.log import logger

from firecrawl import FirecrawlApp


class FirecrawlReader(Reader):
    api_key: Optional[str] = None
    params: Optional[Dict] = None
    mode: Literal["scrape", "crawl"] = "scrape"

    def scrape(self, url: str) -> List[Document]:
        """
        Scrapes a website and returns a list of documents.

        Args:
            url: The URL of the website to scrape

        Returns:
            A list of documents
        """

        logger.debug(f"Scraping: {url}")

        app = FirecrawlApp(api_key=self.api_key)
        scraped_data = app.scrape_url(url, params=self.params)
        content = scraped_data.get("content")
        metadata = scraped_data.get("metadata")

        documents = []
        if self.chunk:
            documents.extend(self.chunk_document(Document(name=url, id=url, meta_data=metadata, content=content)))
        else:
            documents.append(Document(name=url, id=url, meta_data=metadata, content=content))
        return documents

    def crawl(self, url: str) -> List[Document]:
        """
        Craws a website and returns a list of documents.

        Args:
            url: The URL of the website to scrape

        Returns:
            A list of documents
        """

        logger.debug(f"Crawling: {url}")

        app = FirecrawlApp(api_key=self.api_key)
        crawl_result = app.crawl_url(url, params=self.params)
        documents = []
        for result in crawl_result:
            content = result.get("content")
            metadata = result.get("metadata")

            if self.chunk:
                documents.extend(self.chunk_document(Document(name=url, id=url, meta_data=metadata, content=content)))
            else:
                documents.append(Document(name=url, id=url, meta_data=metadata, content=content))
        return documents

    def read(self, url: str) -> List[Document]:
        """

        Args:
            url: The URL of the website to scrape

        Returns:
            A list of documents
        """

        if self.mode == "scrape":
            return self.scrape(url)
        elif self.mode == "crawl":
            return self.crawl(url)
        else:
            raise NotImplementedError(f"Mode {self.mode} not implemented")
