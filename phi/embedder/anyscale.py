from os import getenv
from typing import Optional

from phi.embedder.openai import OpenAIEmbedder


class AnyscaleEmbedder(OpenAIEmbedder):
    model: str = "thenlper/gte-large"
    dimensions: int = 1024
    api_key: Optional[str] = getenv("ANYSCALE_API_KEY")
    base_url: str = "https://api.endpoints.anyscale.com/v1"
