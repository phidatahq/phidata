from os import getenv
from typing import Optional

from phi.model.openai.like import OpenAILike


class Anyscale(OpenAILike):
    """
    Anyscale model class.

    Args:
        id (str): The id of the Anyscale model to use. Default is "mistralai/Mixtral-8x7B-Instruct-v0.1".
        name (str): The name of this chat model instance. Default is "Anyscale"
        provider (str): The provider of the model. Default is "Anyscale".
        api_key (str): The api key to authorize request to Anyscale.
        base_url (str): The base url to which the requests are sent.
    """

    id: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    name: str = "Anyscale"
    provider: str = "Anyscale"
    api_key: Optional[str] = getenv("ANYSCALE_API_KEY")
    base_url: str = "https://api.endpoints.anyscale.com/v1"
