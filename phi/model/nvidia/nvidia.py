from os import getenv
from typing import Optional, Any

from pydantic import model_validator

from phi.model.openai.like import OpenAILike


class Nvidia(OpenAILike):
    """
    A class for interacting with Nvidia models.

    Attributes:
        id (str): The id of the Nvidia model to use. Default is "nvidia/llama-3.1-nemotron-70b-instruct".
        name (str): The name of this chat model instance. Default is "Nvidia"
        provider (str): The provider of the model. Default is "Nvidia".
        api_key (str): The api key to authorize request to Nvidia.
        base_url (str): The base url to which the requests are sent.
    """

    id: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    name: str = "Nvidia"
    provider: str = "Nvidia " + id

    api_key: Optional[str] = getenv("NVIDIA_API_KEY", None)
    base_url: str = "https://integrate.api.nvidia.com/v1"

    @model_validator(mode='before')
    def validate_api_key(cls, data: Any) -> str:
        if 'api_key' not in data or data['api_key'] is None:
            raise ValueError("API key must be set for DeepSeekChat. Set it as an environment variable (DEEPSEEK_API_KEY) or provide it explicitly.")
        return data

