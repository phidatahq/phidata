from os import getenv
from typing import Optional

from phi.llm.openai.like import OpenAILike


class Fireworks(OpenAILike):
    name: str = "Fireworks"
    model: str = "accounts/fireworks/models/firefunction-v1"
    api_key: Optional[str] = getenv("FIREWORKS_API_KEY")
    base_url: str = "https://api.fireworks.ai/inference/v1"
