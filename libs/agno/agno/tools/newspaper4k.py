import json
from typing import Any, Dict, Optional

from agno.tools import Toolkit
from agno.utils.log import logger

try:
    import newspaper
except ImportError:
    raise ImportError("`newspaper4k` not installed. Please run `pip install newspaper4k lxml_html_clean`.")


class Newspaper4kTools(Toolkit):
    def __init__(
        self,
        read_article: bool = True,
        include_summary: bool = False,
        article_length: Optional[int] = None,
    ):
        super().__init__(name="newspaper_tools")

        self.include_summary: bool = include_summary
        self.article_length: Optional[int] = article_length
        if read_article:
            self.register(self.read_article)

    def get_article_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Read and get article data from a URL.

        Args:
            url (str): The URL of the article.

        Returns:
            Dict[str, Any]: The article data.
        """

        try:
            article = newspaper.article(url)
            article_data = {}
            if article.title:
                article_data["title"] = article.title
            if article.authors:
                article_data["authors"] = article.authors
            if article.text:
                article_data["text"] = article.text
            if self.include_summary and article.summary:
                article_data["summary"] = article.summary

            try:
                if article.publish_date:
                    article_data["publish_date"] = article.publish_date.isoformat() if article.publish_date else None
            except Exception:
                pass

            return article_data
        except Exception as e:
            logger.warning(f"Error reading article from {url}: {e}")
            return None

    def read_article(self, url: str) -> str:
        """Use this function to read an article from a URL.

        Args:
            url (str): The URL of the article.

        Returns:
            str: JSON containing the article author, publish date, and text.
        """

        try:
            logger.debug(f"Reading news: {url}")
            article_data = self.get_article_data(url)
            if not article_data:
                return f"Error reading article from {url}: No data found."

            if self.article_length and "text" in article_data:
                article_data["text"] = article_data["text"][: self.article_length]

            return json.dumps(article_data, indent=2)
        except Exception as e:
            return f"Error reading article from {url}: {e}"
