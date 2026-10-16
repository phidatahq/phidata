from dataclasses import dataclass, field
from os import getenv
from typing import Any, Dict, Optional

from agno.exceptions import ModelAuthenticationError
from agno.models.openai.like import OpenAILike


@dataclass
class Linkrra(OpenAILike):
    """
    A class for interacting with Linkrra's Synap API, an OpenAI-compatible endpoint serving
    open-weight models.

    Attributes:
        id (str): The id of the Linkrra model to use. Default is "qwen3-coder-30b".
        name (str): The name of this chat model instance. Default is "Linkrra".
        provider (str): The provider of the model. Default is "Linkrra".
        api_key (str): The api key to authorize request to Linkrra.
        base_url (str): The base url to which the requests are sent. Defaults to "https://pool.linkrra.com/v1".
    """

    id: str = "qwen3-coder-30b"
    name: str = "Linkrra"
    provider: str = "Linkrra"
    api_key: Optional[str] = field(default_factory=lambda: getenv("LINKRRA_API_KEY"))
    base_url: str = "https://pool.linkrra.com/v1"

    def _get_client_params(self) -> Dict[str, Any]:
        """
        Returns client parameters for API requests, checking for LINKRRA_API_KEY.

        Returns:
            Dict[str, Any]: A dictionary of client parameters for API requests.
        """
        if not self.api_key:
            self.api_key = getenv("LINKRRA_API_KEY")
            if not self.api_key:
                raise ModelAuthenticationError(
                    message="LINKRRA_API_KEY not set. Please set the LINKRRA_API_KEY environment variable.",
                    model_name=self.name,
                )
        return super()._get_client_params()
