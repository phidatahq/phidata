from typing import Optional, Dict, Any
from phi.llm.openai.chat import OpenAIChat
from openai import AzureOpenAI as AzureOpenAIClient

class AzureOpenAI(OpenAIChat):
    name: str = "AzureOpenAI"
    model: str = "not-provided"
    api_key: Optional[str] = "not-provided"
    api_version: str = "not-provided"
    azure_endpoint: str = "not-provided"

    phi_proxy: bool = False

    @property
    def client(self) -> AzureOpenAIClient:
        if self.openai_client:
            return self.openai_client

        _azure_openai_params: Dict[str, Any] = {}
        if self.api_key:
            _azure_openai_params["api_key"] = self.api_key
        if self.organization:
            _azure_openai_params["organization"] = self.organization
        if self.base_url:
            _azure_openai_params["azure_endpoint"] = self.base_url
        _azure_openai_params["api_version"] = self.api_version
        if self.client_kwargs:
            _azure_openai_params.update(self.client_kwargs)
        return AzureOpenAIClient(**_azure_openai_params)
    
