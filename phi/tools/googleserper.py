import json
from os import getenv
from typing import Optional, Dict, Any, List

from phi.tools import Toolkit
from phi.utils.log import logger

import http.client

class SerperTool(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        search: bool = True,
        images: bool = True,
        news: bool = True,
        headers: Optional[Any] = None,
        fixed_max_results: Optional[int] = None,
        fixed_language: Optional[str] = None,
    ):
        super().__init__(name="serper")

        self.api_key = api_key or getenv("SERPER_API_KEY")
        if not self.api_key:
            logger.error("SERPER_API_KEY not provided. Please set the SERPER_API_KEY environment variable.")
        
        self.headers: Optional[Any] = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        self.fixed_max_results: Optional[int] = fixed_max_results
        self.fixed_language: Optional[str] = fixed_language

        if search:
            self.register(self.serper_search)
        if news:
            self.register(self.serper_news)
        if images:
            self.register(self.serper_images)

    def serper_search(self, query: str, num: int = 5, country: str = "us") -> str:
        """
        Serper is the world's fastest and cheapest Google Search API.
        Use this function to search from Google Serper for the give user query

        Args:
            query(str): The query to search for.
            num (optional, default=5): The maximum number of results to return.
            country (optional, default-="us"): The country from which the information needs to be searched. 

        Returns:
            The result from Google Serper.
        """
        logger.debug(f"Searching Google Serper for: {query}")
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": query,
            "num": self.fixed_max_results or num,
            "gl": country
        })
        conn.request("POST", "/search", payload, self.headers)
        res = conn.getresponse()
        data = res.read()
        return data
    
    def serper_news(self, query: str, num: int = 5, country: str = "us") -> str:
        """
        Serper is the world's fastest and cheapest Google Search API.
        Use this function to extract news information only from Google Serper for the give user query

        Args:
            query(str): The news information to gather.
            num (optional, default=5): The maximum number of results to return.
            country (optional, default-="us"): The country from which the news needs to fetched. 

        Returns:
            The news information from Google Serper.
        """
        logger.debug(f"Fetching News from Google Serper for: {query}")
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": query,
            "num": self.fixed_max_results or num,
            "gl": country
        })
        conn.request("POST", "/news", payload, self.headers)
        res = conn.getresponse()
        new_data = res.read()
        return new_data
    
    def serper_images(self, query: str, num: int = 5, country: str = "us") -> str:
        """
        Serper is the world's fastest and cheapest Google Search API.
        Use this function to extract images from Google Serper for the give user query

        Args:
            query(str): The images to fetch for this query.
            num (optional, default=5): The maximum number of results to return.
            country (optional, default-="us"): The country from which the images needs to fetched. 

        Returns:
            The images links from Google Serper.
        """
        logger.debug(f"Fetching News from Google Serper for: {query}")
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": query,
            "num": self.fixed_max_results or num,
            "gl": country
        })
        conn.request("POST", "/images", payload, self.headers)
        res = conn.getresponse()
        img_data = res.read()
        return img_data