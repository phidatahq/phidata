import json
from os import getenv
from typing import Optional, Dict, Any, List

from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from exa_py import Exa
except ImportError:
    raise ImportError("`exa_py` not installed. Please install using `pip install exa_py`")


class ExaTools(Toolkit):
    def __init__(
        self,
        text: bool = True,
        text_length_limit: int = 1000,
        highlights: bool = True,
        api_key: Optional[str] = None,
        num_results: Optional[int] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        include_domains: Optional[List[str]] = None,
        show_results: bool = False,
    ):
        super().__init__(name="exa")

        self.api_key = api_key or getenv("EXA_API_KEY")
        if not self.api_key:
            logger.error("EXA_API_KEY not set. Please set the EXA_API_KEY environment variable.")

        self.show_results = show_results

        self.text: bool = text
        self.text_length_limit: int = text_length_limit
        self.highlights: bool = highlights
        self.num_results: Optional[int] = num_results
        self.start_crawl_date: Optional[str] = start_crawl_date
        self.end_crawl_date: Optional[str] = end_crawl_date
        self.start_published_date: Optional[str] = start_published_date
        self.end_published_date: Optional[str] = end_published_date
        self.use_autoprompt: Optional[bool] = use_autoprompt
        self.type: Optional[str] = type
        self.include_domains: Optional[List[str]] = include_domains
        self.category: Optional[str] = category

        self.register(self.search_exa)

    def search_exa(self, query: str, num_results: int = 5) -> str:
        """Use this function to search Exa (a web search engine) for a query.

        Args:
            query (str): The query to search for.
            num_results (int): Number of results to return. Defaults to 5.

        Returns:
            str: The search results in JSON format.
        """
        if not self.api_key:
            return "Please set the EXA_API_KEY"

        try:
            exa = Exa(self.api_key)
            logger.info(f"Searching exa for: {query}")
            search_kwargs: Dict[str, Any] = {
                "text": self.text,
                "highlights": self.highlights,
                "num_results": self.num_results or num_results,
                "start_crawl_date": self.start_crawl_date,
                "end_crawl_date": self.end_crawl_date,
                "start_published_date": self.start_published_date,
                "end_published_date": self.end_published_date,
                "use_autoprompt": self.use_autoprompt,
                "type": self.type,
                "category": self.category,
                "include_domains": self.include_domains,
            }
            # Clean up the kwargs
            search_kwargs = {k: v for k, v in search_kwargs.items() if v is not None}
            exa_results = exa.search_and_contents(query, **search_kwargs)
            exa_results_parsed = []
            for result in exa_results.results:
                result_dict = {"url": result.url}
                if result.title:
                    result_dict["title"] = result.title
                if result.author and result.author != "":
                    result_dict["author"] = result.author
                if result.published_date:
                    result_dict["published_date"] = result.published_date
                if result.text:
                    _text = result.text
                    if self.text_length_limit:
                        _text = _text[: self.text_length_limit]
                    result_dict["text"] = _text
                if self.highlights:
                    try:
                        if result.highlights:  # type: ignore
                            result_dict["highlights"] = result.highlights  # type: ignore
                    except Exception as e:
                        logger.debug(f"Failed to get highlights {e}")
                exa_results_parsed.append(result_dict)
            parsed_results = json.dumps(exa_results_parsed, indent=4)
            if self.show_results:
                logger.info(parsed_results)
            return parsed_results
        except Exception as e:
            logger.error(f"Failed to search exa {e}")
            return f"Error: {e}"
