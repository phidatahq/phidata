from os import getenv
from typing import Optional

from phi.llm.openai.like import OpenAILike


class OpenRouter(OpenAILike):
    name: str = "OpenRouter"
    model: str = "mistralai/mistral-7b-instruct:free"
    api_key: Optional[str] = getenv("OPENROUTER_API_KEY")
    base_url: str = "https://openrouter.ai/api/v1"
