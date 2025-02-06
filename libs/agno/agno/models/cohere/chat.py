from dataclasses import dataclass
from os import getenv
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Tuple


from agno.models.base import MessageData, Model
from agno.models.message import Message
from agno.models.response import ModelResponse, ProviderResponse
from agno.utils.log import logger

try:
    from cohere import AsyncClientV2 as CohereAsyncClient
    from cohere import ClientV2 as CohereClient
    from cohere.types.streamed_chat_response_v2 import StreamedChatResponseV2
    from cohere.types.chat_response import ChatResponse
except (ModuleNotFoundError, ImportError):
    raise ImportError("`cohere` not installed. Please install using `pip install cohere`")

@dataclass
class CohereResponseUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

@dataclass
class Cohere(Model):
    id: str = "command-r-plus"
    name: str = "cohere"
    provider: str = "Cohere"

    # -*- Request parameters
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    seed: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    logprobs: Optional[bool] = None
    request_params: Optional[Dict[str, Any]] = None
    # Add chat history to the cohere messages instead of using the conversation_id
    add_chat_history: bool = False
    # -*- Client parameters
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    # -*- Provide the Cohere client manually
    client: Optional[CohereClient] = None
    async_client: Optional[CohereAsyncClient] = None

    def get_client(self) -> CohereClient:
        if self.client:
            return self.client

        _client_params: Dict[str, Any] = {}

        self.api_key = self.api_key or getenv("CO_API_KEY")
        if not self.api_key:
            logger.error("CO_API_KEY not set. Please set the CO_API_KEY environment variable.")

        _client_params["api_key"] = self.api_key

        self.client = CohereClient(**_client_params)
        return self.client

    def get_async_client(self) -> CohereAsyncClient:
        if self.async_client:
            return self.async_client

        _client_params: Dict[str, Any] = {}

        self.api_key = self.api_key or getenv("CO_API_KEY")

        if not self.api_key:
            logger.error("CO_API_KEY not set. Please set the CO_API_KEY environment variable.")

        _client_params["api_key"] = self.api_key

        self.async_client = CohereAsyncClient(**_client_params)
        return self.async_client

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        _request_params: Dict[str, Any] = {}
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.top_k:
            _request_params["k"] = self.top_k
        if self.top_p:
            _request_params["p"] = self.top_p
        if self.seed:
            _request_params["seed"] = self.seed
        if self.logprobs:
            _request_params["logprobs"] = self.logprobs
        if self.frequency_penalty:
            _request_params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty:
            _request_params["presence_penalty"] = self.presence_penalty

        if self._tools is not None and len(self._tools) > 0:
            _request_params["tools"] = self._tools
            if self.tool_choice is not None:
                _request_params["tool_choice"] = self.tool_choice

        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params


    def _format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Format messages for the Cohere API.

        Args:
            messages (List[Message]): The list of messages.

        Returns:
            List[Dict[str, Any]]: The formatted messages.
        """
        formatted_messages = []
        for m in messages:
            m_dict = m.to_dict()
            if m_dict["content"] is None:
                m_dict.pop("content")
            formatted_messages.append(m_dict)
        return formatted_messages

    def invoke(
        self, messages: List[Message]
    ) -> ChatResponse:
        """
        Invoke a non-streamed chat response from the Cohere API.

        Args:
            messages (List[Message]): The list of messages.

        Returns:
            ChatResponse: The chat response.
        """

        request_kwargs = self.request_kwargs

        return self.get_client().chat(model=self.id, messages=self._format_messages(messages), **request_kwargs)

    def invoke_stream(
        self, messages: List[Message]
    ) -> Iterator[StreamedChatResponseV2]:
        """
        Invoke a streamed chat response from the Cohere API.

        Args:
            messages (List[Message]): The list of messages.

        Returns:
            Iterator[StreamedChatResponseV2]: An iterator of streamed chat responses.
        """
        request_kwargs = self.request_kwargs
        return self.get_client().chat_stream(model=self.id, messages=self._format_messages(messages), **request_kwargs)

    async def ainvoke(
        self, messages: List[Message]
    ) -> ChatResponse:
        """
        Asynchronously invoke a non-streamed chat response from the Cohere API.

        Args:
            messages (List[Message]): The list of messages.

        Returns:
            ChatResponse: The chat response.
        """
        request_kwargs = self.request_kwargs

        return await self.get_async_client().chat(model=self.id, messages=self._format_messages(messages), **request_kwargs)

    async def ainvoke_stream(
        self, messages: List[Message]
    ) -> AsyncIterator[StreamedChatResponseV2]:
        """
        Asynchronously invoke a streamed chat response from the Cohere API.

        Args:
            messages (List[Message]): The list of messages.

        Returns:
            AsyncIterator[StreamedChatResponseV2]: An async iterator of streamed chat responses.
        """
        request_kwargs = self.request_kwargs

        async for response in self.get_async_client().chat_stream(model=self.id, messages=self._format_messages(messages), **request_kwargs):
            yield response

    def parse_model_provider_response(self, response: ChatResponse) -> ProviderResponse:
        """
        Parse the model provider response.

        Args:
            response (ChatResponse): The response from the Cohere API.
        """
        provider_response = ProviderResponse()

        provider_response.role = response.message.role

        response_message = response.message
        if response_message.content is not None:
            full_content = ""
            for item in response_message.content:
                full_content += item.text
            provider_response.content = full_content

        if response_message.tool_calls is not None:
            provider_response.tool_calls = [t.model_dump() for t in response_message.tool_calls]

        if response.usage is not None and response.usage.tokens is not None:
            provider_response.response_usage = CohereResponseUsage(
                input_tokens=int(response.usage.tokens.input_tokens) or 0,
                output_tokens=int(response.usage.tokens.output_tokens) or 0,
                total_tokens=int(response.usage.tokens.input_tokens + response.usage.tokens.output_tokens) or 0,
            )

        return provider_response

    def _handle_stream_response(
        self,
        response: StreamedChatResponseV2,
        assistant_message: Message,
        stream_data: MessageData,
        tool_use: Dict[str, Any]
    ) -> Tuple[ModelResponse, Dict[str, Any]]:
        """
        Common handler for processing stream responses from Cohere.

        Args:
            response: The streamed response from Cohere
            assistant_message: The assistant message being built
            stream_data: Data accumulated during streaming
            tool_use: Current tool use data being built

        Returns:
            Tuple containing the ModelResponse to yield and updated tool_use dict
        """
        model_response = None

        if (response.type == "content-delta" and
            response.delta.message is not None and
            response.delta.message.content is not None):

            # Update metrics
            assistant_message.metrics.completion_tokens += 1
            if not assistant_message.metrics.time_to_first_token:
                assistant_message.metrics.set_time_to_first_token()

            # Update provider response content
            stream_data.response_content += response.delta.message.content.text
            model_response = ModelResponse(content=response.delta.message.content.text)

        elif response.type == "tool-call-start":
            if response.delta.message is not None:
                tool_use = response.delta.message.tool_calls.model_dump()

        elif response.type == "tool-call-delta":
            if response.delta.message is not None and response.delta.message.tool_calls is not None:
                tool_use["function"]["arguments"] += response.delta.message.tool_calls.function.arguments

        elif response.type == "tool-call-end":
            if assistant_message.tool_calls is None:
                assistant_message.tool_calls = []
            assistant_message.tool_calls.append(tool_use)
            tool_use = {}

        elif response.type == "message-end":
            if response.delta is not None and response.delta.usage is not None and response.delta.usage.tokens is not None:
                self.add_usage_metrics_to_assistant_message(
                    assistant_message=assistant_message,
                    response_usage=CohereResponseUsage(
                        input_tokens=response.delta.usage.tokens.input_tokens,
                        output_tokens=response.delta.usage.tokens.output_tokens,
                        total_tokens=response.delta.usage.tokens.input_tokens + response.delta.usage.tokens.output_tokens,
                    )
                )

        return model_response, tool_use

    def process_response_stream(
        self,
        messages: List[Message],
        assistant_message: Message,
        stream_data: MessageData
    ) -> Iterator[ModelResponse]:
        """Process the synchronous response stream."""
        tool_use: Dict[str, Any] = {}

        for response in self.invoke_stream(messages=messages):
            model_response, tool_use = self._handle_stream_response(
                response=response,
                assistant_message=assistant_message,
                stream_data=stream_data,
                tool_use=tool_use
            )
            if model_response is not None:
                yield model_response

    async def aprocess_response_stream(
        self,
        messages: List[Message],
        assistant_message: Message,
        stream_data: MessageData
    ) -> AsyncIterator[ModelResponse]:
        """Process the asynchronous response stream."""
        tool_use: Dict[str, Any] = {}

        async for response in self.ainvoke_stream(messages=messages):
            model_response, tool_use = self._handle_stream_response(
                response=response,
                assistant_message=assistant_message,
                stream_data=stream_data,
                tool_use=tool_use
            )
            if model_response is not None:
                yield model_response

    def parse_model_provider_response_stream(
        self, response: Any
    ) -> Iterator[ProviderResponse]:
        pass
