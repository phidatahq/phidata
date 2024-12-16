from os import getenv
from typing import Optional, Any

from pydantic import model_validator

from phi.model.openai.like import OpenAILike


class OpenRouter(OpenAILike):
    """
    A class for using models hosted on OpenRouter.

    Attributes:
        id (str): The model id. Defaults to "gpt-4o".
        name (str): The model name. Defaults to "OpenRouter".
        provider (str): The provider name. Defaults to "OpenRouter: " + id.
        api_key (Optional[str]): The API key. Defaults to None.
        base_url (str): The base URL. Defaults to "https://openrouter.ai/api/v1".
        max_tokens (int): The maximum number of tokens. Defaults to 1024.
    """

    id: str = "gpt-4o"
    name: str = "OpenRouter"
    provider: str = "OpenRouter: " + id

    api_key: Optional[str] = getenv("OPENROUTER_API_KEY")
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 1024

    @model_validator(mode="before")
    def validate_api_key(cls, data: Any) -> str:
        if "api_key" not in data or data["api_key"] is None:
            raise ValueError(
                "API key must be set for OpenRouter. Set it as an environment variable (OPENROUTER_API_KEY) or provide it explicitly."
            )
        return data
