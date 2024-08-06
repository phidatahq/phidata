from typing import Optional
from os import getenv

from phi.llm.openai.like import OpenAILike


class DeepSeekChat(OpenAILike):
    name: str = "DeepSeekChat"
    model: str = "deepseek-chat"
    api_key: Optional[str] = getenv("DEEPSEEK_API_KEY")
    base_url: str = "https://api.deepseek.com"
