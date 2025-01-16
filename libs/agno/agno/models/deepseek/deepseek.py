from dataclasses import dataclass
from os import getenv
from typing import Optional

from agno.models.openai.like import OpenAILike


@dataclass
class DeepSeek(OpenAILike):
    """
    A model class for DeepSeek Chat API.

    Attributes:
    - id: str: The unique identifier of the model. Default: "deepseek-chat".
    - name: str: The name of the model. Default: "DeepSeek".
    - provider: str: The provider of the model. Default: "DeepSeek".
    - api_key: Optional[str]: The API key for the model.
    - base_url: str: The base URL for the model. Default: "https://api.deepseek.com".
    """

    id: str = "deepseek-chat"
    name: str = "DeepSeek"
    provider: str = "DeepSeek"

    api_key: Optional[str] = getenv("DEEPSEEK_API_KEY", None)
    base_url: str = "https://api.deepseek.com"
