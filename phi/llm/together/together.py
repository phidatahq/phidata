from os import getenv
from typing import Optional

from phi.llm.openai.like import OpenAILike


class Together(OpenAILike):
    name: str = "Together"
    model: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    api_key: Optional[str] = getenv("TOGETHER_API_KEY")
    base_url: str = "https://api.together.xyz/v1"
