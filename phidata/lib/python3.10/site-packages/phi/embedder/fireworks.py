from os import getenv
from typing import Optional

from phi.embedder.openai import OpenAIEmbedder


class FireworksEmbedder(OpenAIEmbedder):
    model: str = "nomic-ai/nomic-embed-text-v1.5"
    dimensions: int = 768
    api_key: Optional[str] = getenv("FIREWORKS_API_KEY")
    base_url: str = "https://api.fireworks.ai/inference/v1"
