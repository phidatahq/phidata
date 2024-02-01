from typing import Optional, List, Iterator, Dict, Any, Mapping, Literal

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.utils.log import logger

try:
    from ollama import Client as OllamaClient, Options as OllaOptions
except ImportError:
    logger.error("`import ollama` not installed")
    raise


class Ollama(LLM):
    name: str = "Ollama"
    model: str = "llama2"
    host: Optional[str] = None
    timeout: Optional[Any] = None
    format: Literal["", "json"] = ""
    options: Optional[OllaOptions] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    ollama_client: Optional[OllamaClient] = None

    @property
    def client(self) -> OllamaClient:
        if self.ollama_client:
            return self.ollama_client

        _ollama_params: Dict[str, Any] = {}
        if self.host:
            _ollama_params["host"] = self.host
        if self.timeout:
            _ollama_params["timeout"] = self.timeout
        if self.client_kwargs:
            _ollama_params.update(self.client_kwargs)
        return OllamaClient(**_ollama_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.response_format is not None:
            if self.response_format.get("type") == "json_object":
                kwargs["format"] = "json"
        if self.options is not None:
            kwargs["options"] = self.options
        return kwargs

    def invoke_model(self, messages: List[Message]) -> Mapping[str, Any]:
        return self.client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            **self.api_kwargs,
        )

    def invoke_model_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        yield from self.client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            stream=True,
            **self.api_kwargs,
        )  # type: ignore
