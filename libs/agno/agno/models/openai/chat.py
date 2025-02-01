from dataclasses import dataclass
from os import getenv
from typing import Any, Dict, Iterator, List, Optional, Union

import httpx
from pydantic import BaseModel

from agno.media import AudioOutput
from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse
from agno.utils.log import logger

try:
    from openai import AsyncOpenAI as AsyncOpenAIClient
    from openai import OpenAI as OpenAIClient
    from openai.types.chat.chat_completion import ChatCompletion
    from openai.types.chat.chat_completion_chunk import (
        ChatCompletionChunk,
        ChoiceDelta,
        ChoiceDeltaToolCall,
    )
    from openai.types.chat.chat_completion_message import ChatCompletionAudio, ChatCompletionMessage
    from openai.types.chat.parsed_chat_completion import ParsedChatCompletion
    from openai.types.completion_usage import CompletionUsage
except ModuleNotFoundError:
    raise ImportError("`openai` not installed. Please install using `pip install openai`")


@dataclass
class StreamData:
    response_content: str = ""
    response_audio: Optional[ChatCompletionAudio] = None
    response_tool_calls: Optional[List[ChoiceDeltaToolCall]] = None


@dataclass
class OpenAIChat(Model):
    """
    A class for interacting with OpenAI models.

    For more information, see: https://platform.openai.com/docs/api-reference/chat/create
    """

    id: str = "gpt-4o"
    name: str = "OpenAIChat"
    provider: str = "OpenAI"
    supports_structured_outputs: bool = True

    # Request parameters
    store: Optional[bool] = None
    reasoning_effort: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Any] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    modalities: Optional[List[str]] = None
    audio: Optional[Dict[str, Any]] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[Any] = None
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    temperature: Optional[float] = None
    user: Optional[str] = None
    top_p: Optional[float] = None
    extra_headers: Optional[Any] = None
    extra_query: Optional[Any] = None
    request_params: Optional[Dict[str, Any]] = None

    # Client parameters
    api_key: Optional[str] = None
    organization: Optional[str] = None
    base_url: Optional[Union[str, httpx.URL]] = None
    timeout: Optional[float] = None
    max_retries: Optional[int] = None
    default_headers: Optional[Any] = None
    default_query: Optional[Any] = None
    http_client: Optional[httpx.Client] = None
    client_params: Optional[Dict[str, Any]] = None

    # OpenAI clients
    client: Optional[OpenAIClient] = None
    async_client: Optional[AsyncOpenAIClient] = None

    # Internal parameters. Not used for API requests
    # Whether to use the structured outputs with this Model.
    structured_outputs: bool = False
    # Whether to override the system role.
    override_system_role: bool = True
    # The role to map the system message to.
    system_message_role: str = "developer"

    def _get_client_params(self) -> Dict[str, Any]:
        # Fetch API key from env if not already set
        if not self.api_key:
            self.api_key = getenv("OPENAI_API_KEY")
            if not self.api_key:
                logger.error("OPENAI_API_KEY not set. Please set the OPENAI_API_KEY environment variable.")

        # Define base client params
        base_params = {
            "api_key": self.api_key,
            "organization": self.organization,
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

    def get_client(self) -> OpenAIClient:
        """
        Returns an OpenAI client.

        Returns:
            OpenAIClient: An instance of the OpenAI client.
        """
        if self.client:
            return self.client

        client_params: Dict[str, Any] = self._get_client_params()
        if self.http_client is not None:
            client_params["http_client"] = self.http_client

        self.client = OpenAIClient(**client_params)
        return self.client

    def get_async_client(self) -> AsyncOpenAIClient:
        """
        Returns an asynchronous OpenAI client.

        Returns:
            AsyncOpenAIClient: An instance of the asynchronous OpenAI client.
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
        return AsyncOpenAIClient(**client_params)

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """
        Returns keyword arguments for API requests.

        Returns:
            Dict[str, Any]: A dictionary of keyword arguments for API requests.
        """
        # Define base request parameters
        base_params = {
            "store": self.store,
            "reasoning_effort": self.reasoning_effort,
            "frequency_penalty": self.frequency_penalty,
            "logit_bias": self.logit_bias,
            "logprobs": self.logprobs,
            "top_logprobs": self.top_logprobs,
            "max_tokens": self.max_tokens,
            "max_completion_tokens": self.max_completion_tokens,
            "modalities": self.modalities,
            "audio": self.audio,
            "presence_penalty": self.presence_penalty,
            "response_format": self.response_format,
            "seed": self.seed,
            "stop": self.stop,
            "temperature": self.temperature,
            "user": self.user,
            "top_p": self.top_p,
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
                "store": self.store,
                "frequency_penalty": self.frequency_penalty,
                "logit_bias": self.logit_bias,
                "logprobs": self.logprobs,
                "top_logprobs": self.top_logprobs,
                "max_tokens": self.max_tokens,
                "max_completion_tokens": self.max_completion_tokens,
                "modalities": self.modalities,
                "audio": self.audio,
                "presence_penalty": self.presence_penalty,
                "response_format": self.response_format
                if isinstance(self.response_format, dict)
                else str(self.response_format),
                "seed": self.seed,
                "stop": self.stop,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "user": self.user,
                "extra_headers": self.extra_headers,
                "extra_query": self.extra_query,
            }
        )
        if self.tools is not None:
            model_dict["tools"] = self.tools
            if self.tool_choice is None:
                model_dict["tool_choice"] = "auto"
            else:
                model_dict["tool_choice"] = self.tool_choice
        cleaned_dict = {k: v for k, v in model_dict.items() if v is not None}
        return cleaned_dict

    def format_message(self, message: Message) -> Dict[str, Any]:
        """
        Format a message into the format expected by OpenAI.

        Args:
            message (Message): The message to format.

        Returns:
            Dict[str, Any]: The formatted message.
        """
        if message.role == "user":
            if message.images is not None:
                message = self.add_images_to_message(message=message, images=message.images)

            if message.audio is not None:
                message = self.add_audio_to_message(message=message, audio=message.audio)

            if message.videos is not None:
                logger.warning("Video input is currently unsupported.")

        # OpenAI expects the tool_calls to be None if empty, not an empty list
        if message.tool_calls is not None and len(message.tool_calls) == 0:
            message.tool_calls = None

        return message.to_dict()

    def invoke(self, messages: List[Message]) -> Union[ChatCompletion, ParsedChatCompletion]:
        """
        Send a chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            ChatCompletion: The chat completion response from the API.
        """
        if self.response_format is not None and self.structured_outputs:
            try:
                if isinstance(self.response_format, type) and issubclass(self.response_format, BaseModel):
                    return self.get_client().beta.chat.completions.parse(
                        model=self.id,
                        messages=[self.format_message(m) for m in messages],  # type: ignore
                        **self.request_kwargs,
                    )
                else:
                    raise ValueError("response_format must be a subclass of BaseModel if structured_outputs=True")
            except Exception as e:
                logger.error(f"Error from OpenAI API: {e}")

        return self.get_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            **self.request_kwargs,
        )

    async def ainvoke(self, messages: List[Message]) -> Union[ChatCompletion, ParsedChatCompletion]:
        """
        Sends an asynchronous chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            ChatCompletion: The chat completion response from the API.
        """
        if self.response_format is not None and self.structured_outputs:
            try:
                if isinstance(self.response_format, type) and issubclass(self.response_format, BaseModel):
                    return await self.get_async_client().beta.chat.completions.parse(
                        model=self.id,
                        messages=[self.format_message(m) for m in messages],  # type: ignore
                        **self.request_kwargs,
                    )
                else:
                    raise ValueError("response_format must be a subclass of BaseModel if structured_outputs=True")
            except Exception as e:
                logger.error(f"Error from OpenAI API: {e}")

        return await self.get_async_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            **self.request_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Iterator[ChatCompletionChunk]:
        """
        Send a streaming chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Iterator[ChatCompletionChunk]: An iterator of chat completion chunks.
        """
        yield from self.get_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            stream=True,
            stream_options={"include_usage": True},
            **self.request_kwargs,
        )  # type: ignore

    async def ainvoke_stream(self, messages: List[Message]) -> Any:
        """
        Sends an asynchronous streaming chat completion request to the OpenAI API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Any: An asynchronous iterator of chat completion chunks.
        """
        async_stream = await self.get_async_client().chat.completions.create(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            stream=True,
            stream_options={"include_usage": True},
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
        if response_usage.prompt_tokens_details is not None:
            if isinstance(response_usage.prompt_tokens_details, dict):
                assistant_message.metrics.prompt_tokens_details = response_usage.prompt_tokens_details
            elif isinstance(response_usage.prompt_tokens_details, BaseModel):
                assistant_message.metrics.prompt_tokens_details = response_usage.prompt_tokens_details.model_dump(
                    exclude_none=True
                )
        if response_usage.completion_tokens_details is not None:
            if isinstance(response_usage.completion_tokens_details, dict):
                assistant_message.metrics.completion_tokens_details = response_usage.completion_tokens_details
            elif isinstance(response_usage.completion_tokens_details, BaseModel):
                assistant_message.metrics.completion_tokens_details = (
                    response_usage.completion_tokens_details.model_dump(exclude_none=True)
                )

    def populate_assistant_message(
        self,
        assistant_message: Message,
        response_message: ChatCompletionMessage,
        response_usage: Optional[CompletionUsage],
    ) -> Message:
        """
        Populate an assistant message with the response message and usage.

        Args:
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

        # -*- Add audio transcript to content if available
        response_audio: Optional[ChatCompletionAudio] = response_message.audio
        if response_audio and response_audio.transcript and not assistant_message.content:
            assistant_message.content = response_audio.transcript

        # -*- Add tool calls to assistant message
        if response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            try:
                assistant_message.tool_calls = [t.model_dump() for t in response_message.tool_calls]
            except Exception as e:
                logger.warning(f"Error processing tool calls: {e}")

        # -*- Add audio to assistant message
        if hasattr(response_message, "audio") and response_message.audio is not None:
            try:
                assistant_message.audio_output = AudioOutput(
                    id=response_message.audio.id,
                    content=response_message.audio.data,
                    expires_at=response_message.audio.expires_at,
                    transcript=response_message.audio.transcript,
                )
            except Exception as e:
                logger.warning(f"Error processing audio: {e}")

        # -*- Add usage metrics to assistant message
        self.add_usage_metrics_to_assistant_message(assistant_message=assistant_message, response_usage=response_usage)
        return assistant_message

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Generate a response from OpenAI.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            ModelResponse: The model response.
        """
        logger.debug(f"---------- {self.get_provider()} Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        # -*- Create assistant message
        assistant_message = Message(role=self.assistant_message_role)

        # -*- Generate response
        assistant_message.metrics.start_timer()
        response: Union[ChatCompletion, ParsedChatCompletion] = self.invoke(messages=messages)
        assistant_message.metrics.stop_timer()

        # -*- Parse response message
        response_message: ChatCompletionMessage = response.choices[0].message
        # -*- Parse structured outputs
        try:
            if (
                self.response_format is not None
                and self.structured_outputs
                and issubclass(self.response_format, BaseModel)
            ):
                parsed_object = response_message.parsed  # type: ignore
                if parsed_object is not None:
                    model_response.parsed = parsed_object
        except Exception as e:
            logger.warning(f"Error retrieving structured outputs: {e}")

        # -*- Populate the assistant message with response message and usage
        self.populate_assistant_message(
            assistant_message=assistant_message,
            response_message=response_message,
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
        if assistant_message.audio_output is not None:
            # add the audio to the model response
            model_response.audio = assistant_message.audio_output

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
        logger.debug(f"---------- {self.get_provider()} Response End ----------")
        return model_response

    async def aresponse(self, messages: List[Message]) -> ModelResponse:
        """
        Generate an asynchronous response from OpenAI.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            ModelResponse: The model response from the API.
        """
        logger.debug(f"---------- {self.get_provider()} Async Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        # -*- Create assistant message
        assistant_message = Message(role=self.assistant_message_role)

        # -*- Generate response
        assistant_message.metrics.start_timer()
        response: Union[ChatCompletion, ParsedChatCompletion] = await self.ainvoke(messages=messages)
        assistant_message.metrics.stop_timer()

        # -*- Parse response
        response_message: ChatCompletionMessage = response.choices[0].message
        # -*- Parse structured outputs
        try:
            if (
                self.response_format is not None
                and self.structured_outputs
                and issubclass(self.response_format, BaseModel)
            ):
                parsed_object = response_message.parsed  # type: ignore
                if parsed_object is not None:
                    model_response.parsed = parsed_object
        except Exception as e:
            logger.warning(f"Error retrieving structured outputs: {e}")

        # -*- Populate the assistant message with response message and usage
        self.populate_assistant_message(
            assistant_message=assistant_message,
            response_message=response_message,
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
        if assistant_message.audio_output is not None:
            # add the audio to the model response
            model_response.audio = assistant_message.audio_output

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

        logger.debug(f"---------- {self.get_provider()} Async Response End ----------")
        return model_response

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        """
        Generate a streaming response from OpenAI.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            Iterator[ModelResponse]: An iterator of model responses.
        """
        logger.debug(f"---------- {self.get_provider()} Response Start ----------")
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

                if response_delta.content is not None:
                    stream_data.response_content += response_delta.content
                    yield ModelResponse(content=response_delta.content)

                if hasattr(response_delta, "audio"):
                    response_audio = response_delta.audio
                    stream_data.response_audio = response_audio
                    if stream_data.response_audio:
                        yield ModelResponse(
                            audio=AudioOutput(
                                id=stream_data.response_audio.id,
                                content=stream_data.response_audio.data,
                                expires_at=stream_data.response_audio.expires_at,
                                transcript=stream_data.response_audio.transcript,
                            )
                        )

                if response_delta.tool_calls is not None:
                    if stream_data.response_tool_calls is None:
                        stream_data.response_tool_calls = []
                    stream_data.response_tool_calls.extend(response_delta.tool_calls)

            if response.usage is not None:
                self.add_usage_metrics_to_assistant_message(
                    assistant_message=assistant_message, response_usage=response.usage
                )
        assistant_message.metrics.stop_timer()

        # -*- Add response content and audio to assistant message
        if stream_data.response_content != "":
            assistant_message.content = stream_data.response_content
        if stream_data.response_audio is not None:
            assistant_message.audio_output = AudioOutput(
                id=stream_data.response_audio.id,
                content=stream_data.response_audio.data,
                expires_at=stream_data.response_audio.expires_at,
                transcript=stream_data.response_audio.transcript,
            )

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
        logger.debug(f"---------- {self.get_provider()} Response End ----------")

    async def aresponse_stream(self, messages: List[Message]) -> Any:
        """
        Generate an asynchronous streaming response from OpenAI.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            Any: An asynchronous iterator of model responses.
        """
        logger.debug(f"---------- {self.get_provider()} Async Response Start ----------")
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

                if response_delta.content is not None:
                    stream_data.response_content += response_delta.content
                    yield ModelResponse(content=response_delta.content)

                if hasattr(response_delta, "audio"):
                    response_audio = response_delta.audio
                    stream_data.response_audio = response_audio
                    if stream_data.response_audio:
                        yield ModelResponse(
                            audio=AudioOutput(
                                id=stream_data.response_audio.id,
                                content=stream_data.response_audio.data,
                                expires_at=stream_data.response_audio.expires_at,
                                transcript=stream_data.response_audio.transcript,
                            )
                        )

                if response_delta.tool_calls is not None:
                    if stream_data.response_tool_calls is None:
                        stream_data.response_tool_calls = []
                    stream_data.response_tool_calls.extend(response_delta.tool_calls)

            if response.usage is not None:
                self.add_usage_metrics_to_assistant_message(
                    assistant_message=assistant_message, response_usage=response.usage
                )
        assistant_message.metrics.stop_timer()

        # -*- Add response content and audio to assistant message
        assistant_message = Message(role="assistant")
        if stream_data.response_content != "":
            assistant_message.content = stream_data.response_content
        if stream_data.response_audio is not None:
            assistant_message.audio_output = AudioOutput(
                id=stream_data.response_audio.id,
                content=stream_data.response_audio.data,
                expires_at=stream_data.response_audio.expires_at,
                transcript=stream_data.response_audio.transcript,
            )

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
        logger.debug(f"---------- {self.get_provider()} Async Response End ----------")
