from typing import Optional
from os import getenv

from phi.model.openai.like import OpenAILike


class Sambanova(OpenAILike):
    id: str = "Meta-Llama-3.1-8B-Instruct"
    name: str = "Sambanova"
    provider: str = "Sambanova"
    api_key: Optional[str] = getenv("SAMBANOVA_API_KEY")
    base_url: str = "https://api.sambanova.ai/v1"
