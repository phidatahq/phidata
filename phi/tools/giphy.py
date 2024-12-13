import uuid
from typing import Optional
import httpx
import os

from phi.agent import Agent
from phi.model.content import Image
from phi.tools import Toolkit
from phi.utils.log import logger


class GiphyTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        limit: int = 1,
    ):
        super().__init__(name="giphy_tools")

        self.api_key = api_key or os.getenv("GIPHY_API_KEY")
        if not self.api_key:
            logger.error("No Giphy API key provided")

        self.limit: int = limit

        self.register(self.search_gifs)

    def search_gifs(self, agent: Agent, query: str) -> str:
        """Find a GIPHY gif

        Args:
            query (str): A text description of the required gif.

        Returns:
            The resulting gif.
        """

        base_url = "https://api.giphy.com/v1/gifs/search"
        params = {
            "api_key": self.api_key,
            "q": query,
            "limit": self.limit,
        }

        try:
            response = httpx.get(base_url, params=params)
            response.raise_for_status()

            # Extract the GIF URLs
            data = response.json()
            gif_urls = [gif["embed_url"] for gif in data.get("data", [])]

            for gif_url in gif_urls:
                media_id = str(uuid.uuid4())
                agent.add_image(Image(id=media_id, url=gif_url, revised_prompt=query))

            return f"These are the found gifs {gif_urls}"

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"An error occurred: {e}")

        return "No gifs found"
