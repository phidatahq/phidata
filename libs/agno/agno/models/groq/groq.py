from dataclasses import dataclass
from os import getenv
from typing import Any, Dict, Iterator, List, Optional, Union

import httpx

from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse
from agno.utils.log import logger

try:
    from groq import AsyncGroq as AsyncGroqClient
    from groq import Groq as GroqClient
    from groq.types.chat import ChatCompletion, ChatCompletionMessage
    from groq.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta, ChoiceDeltaToolCall
    from groq.types.completion_usage import CompletionUsage
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
        if self.tools is not None:
            request_params["tools"] = self.tools
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
                "tools": self.tools,
                "tool_choice": self.tool_choice
                if (self.tools is not None and self.tool_choice is not None)
                else "auto",
            }
        )
        if self.tools is not None:
            model_dict["tools"] = self.tools
            if self.tool_choice is not None:
                model_dict["tool_choice"] = self.tool_choice
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
        yield from self.get_client().chat.completions.create(
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
        async_stream = await self.get_async_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            stream=True,
            **self.request_kwargs,
        )
        async for chunk in async_stream:  # type: ignore
            yield chunk

    def add_usage_metrics_to_assistant_message(self, assistant_message: Message, response_usage: CompletionUsage):
        assistant_message.metrics.input_tokens = response_usage.prompt_tokens
        assistant_message.metrics.output_tokens = response_usage.completion_tokens
        assistant_message.metrics.total_tokens = response_usage.total_tokens

        assistant_message.metrics.prompt_tokens = response_usage.prompt_tokens
        assistant_message.metrics.completion_tokens = response_usage.completion_tokens

        if assistant_message.metrics.additional_metrics is None:
            assistant_message.metrics.additional_metrics = {}
        if response_usage.prompt_time is not None:
            assistant_message.metrics.additional_metrics["prompt_time"] = response_usage.prompt_time
        if response_usage.completion_time is not None:
            assistant_message.metrics.additional_metrics["completion_time"] = response_usage.completion_time
        if response_usage.queue_time is not None:
            assistant_message.metrics.additional_metrics["queue_time"] = response_usage.queue_time
        if response_usage.total_time is not None:
            assistant_message.metrics.additional_metrics["total_time"] = response_usage.total_time

    def populate_assistant_message(
        self,
        assistant_message: Message,
        response_message: ChatCompletionMessage,
        response_usage: Optional[CompletionUsage],
    ) -> Message:
        """
        Populate an assistant message with the response message and usage.

        Args:
            assistant_message (Message): The assistant message to populate.
            response_message (ChatCompletionMessage): The response message.
            response_usage (Optional[CompletionUsage]): The response usage.

        Returns:
            Message: The assistant message.
        """
        # -*- Update role
        if response_message.role:
            assistant_message.role = response_message.role

        # -*- Add content to assistant message
        if response_message.content is not None:
            assistant_message.content = response_message.content

        # -*- Add tool calls to assistant message
        if response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            try:
                assistant_message.tool_calls = [t.model_dump() for t in response_message.tool_calls]
            except Exception as e:
                logger.warning(f"Error processing tool calls: {e}")

        # -*- Add usage metrics to assistant message
        if response_usage is not None:
            self.add_usage_metrics_to_assistant_message(
                assistant_message=assistant_message, response_usage=response_usage
            )
        return assistant_message

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Generate a response from Groq.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            ModelResponse: The model response.
        """
        logger.debug("---------- Groq Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        # -*- Create assistant message
        assistant_message = Message(role=self.assistant_message_role)

        # -*- Generate response
        assistant_message.metrics.start_timer()
        response: ChatCompletion = self.invoke(messages=messages)
        assistant_message.metrics.stop_timer()

        # -*- Populate the assistant message with response message and usage
        self.populate_assistant_message(
            assistant_message=assistant_message,
            response_message=response.choices[0].message,
            response_usage=response.usage,
        )

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()

        # -*- Update model response with assistant message content
        if assistant_message.content is not None:
            # add the content to the model response
            model_response.content = assistant_message.get_content_string()

        # -*- Handle tool calls
        if (
            self.handle_tool_calls(
                assistant_message=assistant_message,
                messages=messages,
                model_response=model_response,
                tool_role=self.tool_message_role,
            )
            is not None
        ):
            return self.handle_post_tool_call_messages(messages=messages, model_response=model_response)
        logger.debug("---------- Groq Response End ----------")
        return model_response

    async def aresponse(self, messages: List[Message]) -> ModelResponse:
        """
        Generate an asynchronous response from Groq.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            ModelResponse: The model response from the API.
        """
        logger.debug("---------- Groq Async Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        # -*- Create assistant message
        assistant_message = Message(role=self.assistant_message_role)

        # -*- Generate response
        assistant_message.metrics.start_timer()
        response: ChatCompletion = await self.ainvoke(messages=messages)
        assistant_message.metrics.stop_timer()

        # -*- Populate the assistant message with response message and usage
        self.populate_assistant_message(
            assistant_message=assistant_message,
            response_message=response.choices[0].message,
            response_usage=response.usage,
        )

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()

        # -*- Update model response with assistant message content and audio
        if assistant_message.content is not None:
            # add the content to the model response
            model_response.content = assistant_message.get_content_string()

        # -*- Handle tool calls
        if (
            await self.ahandle_tool_calls(
                assistant_message=assistant_message,
                messages=messages,
                model_response=model_response,
                tool_role=self.tool_message_role,
            )
            is not None
        ):
            return await self.ahandle_post_tool_call_messages(messages=messages, model_response=model_response)

        logger.debug("---------- Groq Async Response End ----------")
        return model_response

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        """
        Generate a streaming response from Groq.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            Iterator[ModelResponse]: An iterator of model responses.
        """
        logger.debug("---------- Groq Response Start ----------")
        self._log_messages(messages)
        stream_data: StreamData = StreamData()

        # -*- Create assistant message
        assistant_message = Message(role="assistant")

        # -*- Generate response
        assistant_message.metrics.start_timer()
        for response in self.invoke_stream(messages=messages):
            if len(response.choices) > 0:
                assistant_message.metrics.completion_tokens += 1
                if assistant_message.metrics.completion_tokens == 1:
                    assistant_message.metrics.set_time_to_first_token()

                response_delta: ChoiceDelta = response.choices[0].delta
                response_content: Optional[str] = response_delta.content
                response_tool_calls: Optional[List[ChoiceDeltaToolCall]] = response_delta.tool_calls

                if response_content is not None:
                    stream_data.response_content += response_content
                    yield ModelResponse(content=response_content)

                if response_tool_calls is not None:
                    if stream_data.response_tool_calls is None:
                        stream_data.response_tool_calls = []
                    stream_data.response_tool_calls.extend(response_tool_calls)

            if response.usage is not None:
                self.add_usage_metrics_to_assistant_message(
                    assistant_message=assistant_message, response_usage=response.usage
                )
        assistant_message.metrics.stop_timer()

        # -*- Add response content to assistant message
        if stream_data.response_content != "":
            assistant_message.content = stream_data.response_content

        # -*- Add tool calls to assistant message
        if stream_data.response_tool_calls is not None:
            _tool_calls = self.build_tool_calls(stream_data.response_tool_calls)
            if len(_tool_calls) > 0:
                assistant_message.tool_calls = _tool_calls

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log(metrics=True)

        # -*- Handle tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0:
            yield from self.handle_stream_tool_calls(
                assistant_message=assistant_message, messages=messages, tool_role=self.tool_message_role
            )
            yield from self.handle_post_tool_call_messages_stream(messages=messages)
        logger.debug("---------- Groq Response End ----------")

    async def aresponse_stream(self, messages: List[Message]) -> Any:
        """
        Generate an asynchronous streaming response from Groq.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            Any: An asynchronous iterator of model responses.
        """
        logger.debug("---------- Groq Async Response Start ----------")
        self._log_messages(messages)
        stream_data: StreamData = StreamData()

        # -*- Create assistant message
        assistant_message = Message(role="assistant")

        # -*- Generate response
        assistant_message.metrics.start_timer()
        async for response in self.ainvoke_stream(messages=messages):
            if response.choices and len(response.choices) > 0:
                assistant_message.metrics.completion_tokens += 1
                if assistant_message.metrics.completion_tokens == 1:
                    assistant_message.metrics.set_time_to_first_token()

                response_delta: ChoiceDelta = response.choices[0].delta
                response_content = response_delta.content
                response_tool_calls = response_delta.tool_calls

                if response_content is not None:
                    stream_data.response_content += response_content
                    yield ModelResponse(content=response_content)

                if response_tool_calls is not None:
                    if stream_data.response_tool_calls is None:
                        stream_data.response_tool_calls = []
                    stream_data.response_tool_calls.extend(response_tool_calls)

            if response.usage is not None:
                self.add_usage_metrics_to_assistant_message(
                    assistant_message=assistant_message, response_usage=response.usage
                )
        assistant_message.metrics.stop_timer()

        # -*- Add response content to assistant message
        if stream_data.response_content != "":
            assistant_message.content = stream_data.response_content

        # -*- Add tool calls to assistant message
        if stream_data.response_tool_calls is not None:
            _tool_calls = self.build_tool_calls(stream_data.response_tool_calls)
            if len(_tool_calls) > 0:
                assistant_message.tool_calls = _tool_calls

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log(metrics=True)

        # -*- Handle tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0:
            async for tool_call_response in self.ahandle_stream_tool_calls(
                assistant_message=assistant_message, messages=messages, tool_role=self.tool_message_role
            ):
                yield tool_call_response
            async for post_tool_call_response in self.ahandle_post_tool_call_messages_stream(messages=messages):
                yield post_tool_call_response
        logger.debug("---------- Groq Async Response End ----------")
