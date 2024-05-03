from typing import Optional, List, Dict, Any
import json
import requests
from xml.etree import ElementTree
from phi.tools import Toolkit


class Pubmed(Toolkit):
    def __init__(
        self,
        search_term: Optional[str] = None,
        max_results: Optional[int] = None,
        email: Optional[str] = "your_email@example.com",
    ):
        super().__init__(name="pubmed")
        self.search_term = search_term
        self.max_results = max_results
        self.email = email

        self.register(self.search_pubmed)

    def fetch_pubmed_ids(self, search_term: str, max_results: int, email: str) -> List[str]:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": search_term,
            "retmax": max_results,
            "email": email,
            "usehistory": "y",
        }
        response = requests.get(url, params=params)
        root = ElementTree.fromstring(response.content)
        return [id_elem.text for id_elem in root.findall(".//Id")]

    def fetch_details(self, pubmed_ids: List[str]) -> ElementTree.Element:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {"db": "pubmed", "id": ",".join(pubmed_ids), "retmode": "xml"}
        response = requests.get(url, params=params)
        return ElementTree.fromstring(response.content)

    def parse_details(self, xml_root: ElementTree.Element) -> List[Dict[str, Any]]:
        articles = []
        for article in xml_root.findall(".//PubmedArticle"):
            pub_date = article.find(".//PubDate/Year")
            title = article.find(".//ArticleTitle")
            abstract = article.find(".//AbstractText")
            articles.append(
                {
                    "Published": (pub_date.text if pub_date is not None else "No date available"),
                    "Title": title.text if title is not None else "No title available",
                    "Summary": (abstract.text if abstract is not None else "No abstract available"),
                }
            )
        return articles

    def search_pubmed(self, query: str, max_results: int = 10) -> str:
        ids = self.fetch_pubmed_ids(query, max_results, self.email)
        details_root = self.fetch_details(ids)
        articles = self.parse_details(details_root)
        results = [
            f"Published: {article['Published']}\nTitle: {article['Title']}\nSummary:\n{article['Summary']}"
            for article in articles
        ]
        return json.dumps(results)
