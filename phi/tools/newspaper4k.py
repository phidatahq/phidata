import json
from phi.tools import Toolkit

try:
    import newspaper
except ImportError:
    raise ImportError("`newspaper4k` not installed. Please run `pip install newspaper4k lxml_html_clean`.")


class Newspaper4k(Toolkit):
    def __init__(
        self,
        read_article: bool = True,
        include_summary: bool = False,
    ):
        super().__init__(name="newspaper_toolkit")

        self.include_summary: bool = include_summary
        if read_article:
            self.register(self.read_article)

    def read_article(self, url: str) -> str:
        """Get the article information from a URL.

        Args:
            url (str): The URL of the article.

        Returns:
            str: JSON containing the article author, publish date, and text.
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

            return json.dumps(article_data, indent=2)
        except Exception as e:
            return f"Error reading article from {url}: {e}"
