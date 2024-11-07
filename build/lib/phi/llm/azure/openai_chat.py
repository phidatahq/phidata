from os import getenv
from typing import Optional, Dict, Any, List, Iterator
from phi.utils.log import logger
from phi.llm.message import Message
from phi.llm.openai.like import OpenAILike

try:
    from openai import AzureOpenAI as AzureOpenAIClient
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
except ImportError:
    logger.error("`azure openai` not installed")
    raise


class AzureOpenAIChat(OpenAILike):
    name: str = "AzureOpenAIChat"
    model: str
    api_key: Optional[str] = getenv("AZURE_OPENAI_API_KEY")
    api_version: str = getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    azure_endpoint: Optional[str] = getenv("AZURE_OPENAI_ENDPOINT")
    azure_deployment: Optional[str] = getenv("AZURE_DEPLOYMENT")
    base_url: Optional[str] = None
    azure_ad_token: Optional[str] = None
    azure_ad_token_provider: Optional[Any] = None
    organization: Optional[str] = None
    openai_client: Optional[AzureOpenAIClient] = None

    def get_client(self) -> AzureOpenAIClient:
        if self.openai_client:
            return self.openai_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.api_version:
            _client_params["api_version"] = self.api_version
        if self.organization:
            _client_params["organization"] = self.organization
        if self.azure_endpoint:
            _client_params["azure_endpoint"] = self.azure_endpoint
        if self.azure_deployment:
            _client_params["azure_deployment"] = self.azure_deployment
        if self.base_url:
            _client_params["base_url"] = self.base_url
        if self.azure_ad_token:
            _client_params["azure_ad_token"] = self.azure_ad_token
        if self.azure_ad_token_provider:
            _client_params["azure_ad_token_provider"] = self.azure_ad_token_provider
        if self.http_client:
            _client_params["http_client"] = self.http_client
        if self.client_params:
            _client_params.update(self.client_params)

        return AzureOpenAIClient(**_client_params)

    def invoke_stream(self, messages: List[Message]) -> Iterator[ChatCompletionChunk]:
        yield from self.get_client().chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            stream=True,
            **self.api_kwargs,
        )  # type: ignore
