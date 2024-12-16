from os import getenv
from typing import Optional, Any

from pydantic import model_validator

from phi.model.openai.like import OpenAILike


class xAI(OpenAILike):
    """
    Class for interacting with the xAI API.

    Attributes:
        id (str): The ID of the language model.
        name (str): The name of the API.
        provider (str): The provider of the API.
        api_key (Optional[str]): The API key for the xAI API.
        base_url (Optional[str]): The base URL for the xAI API.
    """

    id: str = "grok-beta"
    name: str = "xAI"
    provider: str = "xAI"

    api_key: Optional[str] = getenv("XAI_API_KEY")
    base_url: Optional[str] = "https://api.x.ai/v1"

    @model_validator(mode="before")
    def validate_api_key(cls, data: Any) -> str:
        if "api_key" not in data or data["api_key"] is None:
            raise ValueError(
                "API key must be set for xAI. Set it as an environment variable (XAI_API_KEY) or provide it explicitly."
            )
        return data
