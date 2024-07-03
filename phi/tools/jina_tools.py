from typing import Optional, Dict
import requests
from pydantic import BaseModel, HttpUrl, Field
from phi.tools import Toolkit
from phi.utils.log import logger


class JinaReaderToolsConfig(BaseModel):
    api_key: Optional[str] = Field(None, description="API key for Jina Reader")
    base_url: HttpUrl = Field("https://r.jina.ai/", description="Base URL for Jina Reader API")  # type: ignore
    search_url: HttpUrl = Field("https://s.jina.ai/", description="Search URL for Jina Reader API")  # type: ignore
    max_content_length: int = Field(4000, description="Maximum content length in characters")


class JinaReaderTools(Toolkit):
    def __init__(self, api_key: Optional[str] = None, max_content_length: int = 4000):
        super().__init__(name="jina_reader_tools")
        config = JinaReaderToolsConfig(api_key=api_key, max_content_length=max_content_length)
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.search_url = config.search_url
        self.max_content_length = config.max_content_length

        self.register(self.read_url)
        self.register(self.search_query)

    def read_url(self, url: str) -> str:
        """Reads a URL and returns the truncated content using Jina Reader API."""
        full_url = f"{self.base_url}{url}"
        logger.info(f"Reading URL: {full_url}")
        try:
            response = requests.get(full_url, headers=self._get_headers())
            response.raise_for_status()
            content = response.json()
            return self._truncate_content(str(content))
        except Exception as e:
            error_msg = f"Error reading URL: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def search_query(self, query: str) -> str:
        """Performs a web search using Jina Reader API and returns the truncated results."""
        full_url = f"{self.search_url}{query}"
        logger.info(f"Performing search: {full_url}")
        try:
            response = requests.get(full_url, headers=self._get_headers())
            response.raise_for_status()
            content = response.json()
            return self._truncate_content(str(content))
        except Exception as e:
            error_msg = f"Error performing search: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "X-With-Generated-Alt": "true",
            "X-With-Links-Summary": "true",
            "X-With-Images-Summary": "true",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _truncate_content(self, content: str) -> str:
        """Truncate content to the maximum allowed length."""
        if len(content) > self.max_content_length:
            truncated = content[: self.max_content_length]
            return truncated + "... (content truncated)"
        return content
