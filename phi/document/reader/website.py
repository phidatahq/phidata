import random
import time
from typing import Set, Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from phi.document.base import Document
from phi.document.reader.base import Reader


class WebsiteReader(Reader):
    """Reader for JSON files"""

    chunk: bool = False

    visited: Set[str] = set()
    max_depth: int = 3
    urls_to_crawl: List[Tuple[str, int]] = []

    def delay(self, min_seconds=1, max_seconds=3):
        """
        Introduce a random delay.

        :param min_seconds: Minimum number of seconds to delay. Default is 1.
        :param max_seconds: Maximum number of seconds to delay. Default is 3.
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)

    def _get_primary_domain(self, url: str) -> str:
        """
        Extract primary domain from the given URL.
        """
        domain_parts = urlparse(url).netloc.split(".")
        # Return primary domain (excluding subdomains)
        return ".".join(domain_parts[-2:])

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        # Try to find main content by specific tags or class names
        for tag in ["article", "main"]:
            element = soup.find(tag)
            if element:
                return element.get_text(strip=True, separator=" ")

        for class_name in ["content", "main-content", "post-content"]:
            element = soup.find(class_=class_name)
            if element:
                return element.get_text(strip=True, separator=" ")

        return ""

    def crawl(self, url: str, starting_depth: int = 1) -> Dict[str, str]:
        """
        Crawls and extracts main content text from the given URL and its recursively found links.

        Parameters:
        - url (str): The starting URL to begin the crawl.
        - starting_depth (int, optional): The starting depth level for the crawl. Defaults to 1.

        Returns:
        - Dict[str, str]: A dictionary where each key is a URL and the corresponding value is the main
                          content extracted from that URL.

        Note:
        The function focuses on extracting the main content by prioritizing content inside common HTML tags
        like `<article>`, `<main>`, and `<div>` with class names such as "content", "main-content", etc.
        The crawler will also respect the `max_depth` attribute of the WebCrawler class, ensuring it does not
        crawl deeper than the specified depth.
        """
        aggregated_texts: Dict[str, str] = {}

        primary_domain = self._get_primary_domain(url)
        self.urls_to_crawl.append((url, starting_depth))  # Add starting URL with its depth

        while self.urls_to_crawl:
            current_url, current_depth = self.urls_to_crawl.pop(0)  # Unpack URL and depth

            # If URL is already visited, or does not end with the primary domain, or exceeds max depth, skip
            if (
                current_url in self.visited
                or not urlparse(current_url).netloc.endswith(primary_domain)
                or current_depth > self.max_depth
            ):
                continue

            self.visited.add(current_url)
            self.delay()

            try:
                response = requests.get(current_url, timeout=10)
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract main content
                main_content = self._extract_main_content(soup)
                if main_content:
                    aggregated_texts[current_url] = main_content

                # Add found URLs to the global list, with incremented depth
                for link in soup.find_all("a", href=True):
                    full_url = urljoin(current_url, link["href"])
                    parsed_url = urlparse(full_url)
                    if parsed_url.netloc.endswith(primary_domain) and not any(
                        parsed_url.path.endswith(ext) for ext in [".pdf", ".jpg", ".png"]
                    ):
                        if full_url not in self.visited and (full_url, current_depth + 1) not in self.urls_to_crawl:
                            self.urls_to_crawl.append((full_url, current_depth + 1))

            except requests.RequestException:
                pass

        return aggregated_texts

    def read(self, url:str) -> list:
        """
        Iterates through the dictionary, chunking values longer than 2000 characters.
        It ensures that words aren't split between chunks.

        Parameters:
        - dictionary (dict): Dictionary to process.

        Returns:
        - list: A list of tuples containing key-value pairs.
        """
        crawl_dict = self.crawl(url)
        documents = []

        for current_url, content in crawl_dict.items():
            if len(content) <= 2000:
                print(f"Content: {len(content)} \n {content}\n{'-' * 50}\n")
                documents.append(
                    Document(
                        name=url,
                        meta_data={"url": str(current_url)},
                        content=str(content),
                    )
                )
                continue

            start = 0
            while start < len(content):
                end = start + 2000

                # Ensure we're not breaking words in half
                if end < len(content):  # check if not the last possible character
                    while end > start and content[end] not in [' ', '\n']:
                        end -= 1
                # If the entire chunk is a word longer than 1000 characters, then just split it at 1000.
                if end == start:
                    end = start + 2000

                chunk = content[start:end]
                print(f"Content: {len(chunk)} \n {chunk}\n{'-' * 50}\n")
                documents.append(
                    Document(
                        name=url,
                        meta_data={"url": str(current_url)},
                        content=str(chunk),
                    )
                )
                start = end

        return documents
