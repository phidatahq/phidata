from os import getenv
from typing import Optional
from phi.model.openai.like import OpenAILike


class xAI(OpenAILike):
    id: str = "grok-beta"
    name: str = "xAI"
    provider: str = "xAI"

    api_key: Optional[str] = getenv("XAI_API_KEY")
    base_url: Optional[str] = "https://api.x.ai/v1"
