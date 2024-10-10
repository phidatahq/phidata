from typing import Optional
from os import getenv

from phi.model.openai.like import OpenAILike


class DeepSeekChat(OpenAILike):
    id: str = "deepseek-chat"
    name: str = "DeepSeekChat"
    provider: str = "DeepSeek"
    api_key: Optional[str] = getenv("DEEPSEEK_API_KEY")
    base_url: str = "https://api.deepseek.com"
