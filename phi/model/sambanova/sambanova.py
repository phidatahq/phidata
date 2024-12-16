from typing import Optional, Any
from os import getenv

from pydantic import model_validator

from phi.model.openai.like import OpenAILike


class Sambanova(OpenAILike):
    """
    A class for interacting with Sambanova models.

    Attributes:
        id (str): The id of the Sambanova model to use. Default is "Meta-Llama-3.1-8B-Instruct".
        name (str): The name of this chat model instance. Default is "Sambanova"
        provider (str): The provider of the model. Default is "Sambanova".
        api_key (str): The api key to authorize request to Sambanova.
        base_url (str): The base url to which the requests are sent.
    """

    id: str = "Meta-Llama-3.1-8B-Instruct"
    name: str = "Sambanova"
    provider: str = "Sambanova"

    api_key: Optional[str] = getenv("SAMBANOVA_API_KEY")
    base_url: str = "https://api.sambanova.ai/v1"

    @model_validator(mode='before')
    def validate_api_key(cls, data: Any) -> str:
        if 'api_key' not in data or data['api_key'] is None:
            raise ValueError("API key must be set for Sambanova. Set it as an environment variable (SAMBANOVA_API_KEY) or provide it explicitly.")
        return data
