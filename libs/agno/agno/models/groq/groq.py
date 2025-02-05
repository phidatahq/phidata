from dataclasses import dataclass
from os import getenv
from typing import Any, Dict, Iterator, List, Optional, Union

import httpx

from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelProviderResponse
from agno.utils.log import logger

try:
    from groq import AsyncGroq as AsyncGroqClient
    from groq import Groq as GroqClient
    from groq.types.chat import ChatCompletion
    from groq.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta, ChoiceDeltaToolCall
except (ModuleNotFoundError, ImportError):
    raise ImportError("`groq` not installed. Please install using `pip install groq`")


@dataclass
class StreamData:
    response_content: str = ""
    response_tool_calls: Optional[List[ChoiceDeltaToolCall]] = None


@dataclass
class Groq(Model):
    """
    A class for interacting with Groq models.

    For more information, see: https://console.groq.com/docs/libraries
    """

    id: str = "llama-3.3-70b-versatile"
    name: str = "Groq"
    provider: str = "Groq"

    # Request parameters
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Any] = None
    logprobs: Optional[bool] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    temperature: Optional[float] = None
    top_logprobs: Optional[int] = None
    top_p: Optional[float] = None
    user: Optional[str] = None
    extra_headers: Optional[Any] = None
    extra_query: Optional[Any] = None
    request_params: Optional[Dict[str, Any]] = None

    # Client parameters
    api_key: Optional[str] = None
    base_url: Optional[Union[str, httpx.URL]] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    default_headers: Optional[Any] = None
    default_query: Optional[Any] = None
    http_client: Optional[httpx.Client] = None
    client_params: Optional[Dict[str, Any]] = None

    # Groq clients
    client: Optional[GroqClient] = None
    async_client: Optional[AsyncGroqClient] = None

    def _get_client_params(self) -> Dict[str, Any]:
        # Fetch API key from env if not already set
        if not self.api_key:
            self.api_key = getenv("GROQ_API_KEY")
            if not self.api_key:
                logger.error("GROQ_API_KEY not set. Please set the GROQ_API_KEY environment variable.")

        # Define base client params
        base_params = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "default_headers": self.default_headers,
            "default_query": self.default_query,
        }
        # Create client_params dict with non-None values
        client_params = {k: v for k, v in base_params.items() if v is not None}
        # Add additional client params if provided
        if self.client_params:
            client_params.update(self.client_params)
        return client_params

    def get_client(self) -> GroqClient:
        """
        Returns a Groq client.

        Returns:
            GroqClient: An instance of the Groq client.
        """
        if self.client:
            return self.client

        client_params: Dict[str, Any] = self._get_client_params()
        if self.http_client is not None:
            client_params["http_client"] = self.http_client

        self.client = GroqClient(**client_params)
        return self.client

    def get_async_client(self) -> AsyncGroqClient:
        """
        Returns an asynchronous Groq client.

        Returns:
            AsyncGroqClient: An instance of the asynchronous Groq client.
        """
        if self.async_client:
            return self.async_client

        client_params: Dict[str, Any] = self._get_client_params()
        if self.http_client:
            client_params["http_client"] = self.http_client
        else:
            # Create a new async HTTP client with custom limits
            client_params["http_client"] = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=1000, max_keepalive_connections=100)
            )
        return AsyncGroqClient(**client_params)

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """
        Returns keyword arguments for API requests.

        Returns:
            Dict[str, Any]: A dictionary of keyword arguments for API requests.
        """
        # Define base request parameters
        base_params = {
            "frequency_penalty": self.frequency_penalty,
            "logit_bias": self.logit_bias,
            "logprobs": self.logprobs,
            "max_tokens": self.max_tokens,
            "presence_penalty": self.presence_penalty,
            "response_format": self.response_format,
            "seed": self.seed,
            "stop": self.stop,
            "temperature": self.temperature,
            "top_logprobs": self.top_logprobs,
            "top_p": self.top_p,
            "user": self.user,
            "extra_headers": self.extra_headers,
            "extra_query": self.extra_query,
        }
        # Filter out None values
        request_params = {k: v for k, v in base_params.items() if v is not None}
        # Add tools
        if self._tools is not None:
            request_params["tools"] = self._tools
            if self.tool_choice is not None:
                request_params["tool_choice"] = self.tool_choice
        # Add additional request params if provided
        if self.request_params:
            request_params.update(self.request_params)
        return request_params

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary.

        Returns:
            Dict[str, Any]: The dictionary representation of the model.
        """
        model_dict = super().to_dict()
        model_dict.update(
            {
                "frequency_penalty": self.frequency_penalty,
                "logit_bias": self.logit_bias,
                "logprobs": self.logprobs,
                "max_tokens": self.max_tokens,
                "presence_penalty": self.presence_penalty,
                "response_format": self.response_format,
                "seed": self.seed,
                "stop": self.stop,
                "temperature": self.temperature,
                "top_logprobs": self.top_logprobs,
                "top_p": self.top_p,
                "user": self.user,
                "extra_headers": self.extra_headers,
                "extra_query": self.extra_query,
            }
        )
        if self._tools is not None:
            model_dict["tools"] = self._tools
            if self.tool_choice is not None:
                model_dict["tool_choice"] = self.tool_choice
            else:
                model_dict["tool_choice"] = "auto"
        cleaned_dict = {k: v for k, v in model_dict.items() if v is not None}
        return cleaned_dict

    def format_message(self, message: Message) -> Dict[str, Any]:
        """
        Format a message into the format expected by Groq.

        Args:
            message (Message): The message to format.

        Returns:
            Dict[str, Any]: The formatted message.
        """
        if message.role == "user":
            if message.images is not None:
                message = self.add_images_to_message(message=message, images=message.images)

        return message.to_dict()

    def invoke(self, messages: List[Message]) -> ChatCompletion:
        """
        Send a chat completion request to the Groq API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            ChatCompletion: The chat completion response from the API.
        """
        return self.get_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            **self.request_kwargs,
        )

    async def ainvoke(self, messages: List[Message]) -> ChatCompletion:
        """
        Sends an asynchronous chat completion request to the Groq API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            ChatCompletion: The chat completion response from the API.
        """
        return await self.get_async_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            **self.request_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Iterator[ChatCompletionChunk]:
        """
        Send a streaming chat completion request to the Groq API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Iterator[ChatCompletionChunk]: An iterator of chat completion chunks.
        """
        return self.get_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            stream=True,
            **self.request_kwargs,
        )

    async def ainvoke_stream(self, messages: List[Message]) -> Any:
        """
        Sends an asynchronous streaming chat completion request to the Groq API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Any: An asynchronous iterator of chat completion chunks.
        """
        return await self.get_async_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            stream=True,
            **self.request_kwargs,
        )

    def parse_model_provider_response(
        self, response: ChatCompletion
    ) -> ModelProviderResponse:
        """
        Parse the Groq response into a ModelProviderResponse.

        Args:
            response: Raw response from Groq

        Returns:
            ModelProviderResponse: Parsed response data
        """
        provider_response = ModelProviderResponse()

        # Get response message
        response_message = response.choices[0].message

        # Add role
        if response_message.role is not None:
            provider_response.role = response_message.role

        # Add content
        if response_message.content is not None:
            provider_response.content = response_message.content

        # Add tool calls
        if response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            try:
                provider_response.tool_calls = [t.model_dump() for t in response_message.tool_calls]
            except Exception as e:
                logger.warning(f"Error processing tool calls: {e}")

        # Add usage metrics if present
        if response.usage is not None:
            provider_response.response_usage = response.usage

        return provider_response

    def parse_model_provider_response_stream(
        self, response: ChatCompletionChunk
    ) -> Iterator[ModelProviderResponse]:
        """
        Parse the Groq streaming response into ModelProviderResponse objects.

        Args:
            response: Raw response chunk from Groq

        Returns:
            Iterator[ModelProviderResponse]: Iterator of parsed response data
        """
        if len(response.choices) > 0:
            provider_response = ModelProviderResponse()
            delta: ChoiceDelta = response.choices[0].delta
            has_content = False

            # Add content
            if delta.content is not None:
                provider_response.content = delta.content
                has_content = True

            # Add tool calls
            if delta.tool_calls is not None:
                provider_response.tool_calls = delta.tool_calls
                has_content = True

            # Add usage metrics if present
            if response.usage is not None:
                provider_response.response_usage = response.usage
                has_content = True

            if has_content:
                yield provider_response
