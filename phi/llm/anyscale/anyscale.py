from os import getenv
from typing import Optional

from phi.llm.openai.like import OpenAILike


class Anyscale(OpenAILike):
    name: str = "Anyscale"
    model: str = "meta-llama/Llama-2-70b-chat-hf"
    api_key: Optional[str] = getenv("ANYSCALE_ENDPOINT_API_KEY")
    base_url: str = "https://api.endpoints.anyscale.com/v1"
