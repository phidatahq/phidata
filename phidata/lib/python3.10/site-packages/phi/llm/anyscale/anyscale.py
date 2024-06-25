from os import getenv
from typing import Optional

from phi.llm.openai.like import OpenAILike


class Anyscale(OpenAILike):
    name: str = "Anyscale"
    model: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    api_key: Optional[str] = getenv("ANYSCALE_API_KEY")
    base_url: str = "https://api.endpoints.anyscale.com/v1"
