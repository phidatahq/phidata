import json
from os import getenv
from typing import Optional

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from exa_py import Exa
except ImportError:
    raise ImportError("`exa_py` not installed. Please install using `pip install exa_py`")


class ExaTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        search: bool = False,
        search_with_contents: bool = True,
        show_results: bool = False,
    ):
        super().__init__(name="exa")

        self.api_key = api_key or getenv("EXA_API_KEY")
        if not self.api_key:
            logger.error("EXA_API_KEY not set. Please set the EXA_API_KEY environment variable.")

        self.show_results = show_results
        if search:
            self.register(self.search_exa)
        if search_with_contents:
            self.register(self.search_exa_with_contents)

    def search_exa(self, query: str, num_results: int = 5) -> str:
        """Searches Exa for a query.

        :param query: The query to search for.
        :param num_results: The number of results to return.
        :return: Links of relevant documents from exa.
        """
        if not self.api_key:
            return "Please set the EXA_API_KEY"

        try:
            exa = Exa(self.api_key)
            logger.debug(f"Searching exa for: {query}")
            exa_results = exa.search(query, num_results=num_results)
            exa_search_urls = [result.url for result in exa_results.results]
            parsed_results = "\n".join(exa_search_urls)
            if self.show_results:
                logger.info(parsed_results)
            return parsed_results
        except Exception as e:
            logger.error(f"Failed to search exa {e}")
            return f"Error: {e}"

    def search_exa_with_contents(self, query: str, num_results: int = 3, text_length_limit: int = 1000) -> str:
        """Searches Exa for a query and returns the contents from the search results.

        :param query: The query to search for.
        :param num_results: The number of results to return. Defaults to 3.
        :param text_length_limit: The length of the text to return. Defaults to 1000.
        :return: JSON string of the search results.
        """
        if not self.api_key:
            return "Please set the EXA_API_KEY"

        try:
            exa = Exa(self.api_key)
            logger.debug(f"Searching exa for: {query}")
            exa_results = exa.search_and_contents(query, num_results=num_results)
            exa_results_parsed = []
            for result in exa_results.results:
                result_dict = {"url": result.url}
                if result.text:
                    result_dict["text"] = result.text[:text_length_limit]
                if result.author:
                    result_dict["author"] = result.author
                if result.title:
                    result_dict["title"] = result.title
                exa_results_parsed.append(result_dict)

            parsed_results = json.dumps(exa_results_parsed, indent=2)
            if self.show_results:
                logger.info(parsed_results)
            return parsed_results
        except Exception as e:
            logger.error(f"Failed to search exa {e}")
            return f"Error: {e}"
