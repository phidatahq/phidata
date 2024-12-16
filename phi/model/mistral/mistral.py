from os import getenv
from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Union

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from mistralai import Mistral, models
    from mistralai.models.chatcompletionresponse import ChatCompletionResponse
    from mistralai.models.deltamessage import DeltaMessage
    from mistralai.types.basemodel import Unset
except (ModuleNotFoundError, ImportError):
    raise ImportError("`mistralai` not installed. Please install using `pip install mistralai`")

MistralMessage = Union[models.UserMessage, models.AssistantMessage, models.SystemMessage, models.ToolMessage]


@dataclass
class StreamData:
    response_content: str = ""
    response_tool_calls: Optional[List[Any]] = None
    completion_tokens: int = 0
    response_prompt_tokens: int = 0
    response_completion_tokens: int = 0
    response_total_tokens: int = 0
    time_to_first_token: Optional[float] = None
    response_timer: Timer = field(default_factory=Timer)


class MistralChat(Model):
    """
    MistralChat is a model that uses the Mistral API to generate responses to messages.

    Args:
        id (str): The ID of the model.
        name (str): The name of the model.
        provider (str): The provider of the model.
        temperature (Optional[float]): The temperature of the model.
        max_tokens (Optional[int]): The maximum number of tokens to generate.
        top_p (Optional[float]): The top p of the model.
        random_seed (Optional[int]): The random seed of the model.
        safe_mode (bool): The safe mode of the model.
        safe_prompt (bool): The safe prompt of the model.
        response_format (Optional[Union[Dict[str, Any], ChatCompletionResponse]]): The response format of the model.
        request_params (Optional[Dict[str, Any]]): The request parameters of the model.
        api_key (Optional[str]): The API key of the model.
        endpoint (Optional[str]): The endpoint of the model.
        max_retries (Optional[int]): The maximum number of retries of the model.
        timeout (Optional[int]): The timeout of the model.
        client_params (Optional[Dict[str, Any]]): The client parameters of the model.
        mistral_client (Optional[Mistral]): The Mistral client of the model.

    """

    id: str = "mistral-large-latest"
    name: str = "MistralChat"
    provider: str = "Mistral"

    # -*- Request parameters
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    random_seed: Optional[int] = None
    safe_mode: bool = False
    safe_prompt: bool = False
    response_format: Optional[Union[Dict[str, Any], ChatCompletionResponse]] = None
    request_params: Optional[Dict[str, Any]] = None
    # -*- Client parameters
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    max_retries: Optional[int] = None
    timeout: Optional[int] = None
    client_params: Optional[Dict[str, Any]] = None
    # -*- Provide the MistralClient manually
    mistral_client: Optional[Mistral] = None

    @property
    def client(self) -> Mistral:
        """
        Get the Mistral client.

        Returns:
            Mistral: The Mistral client.
        """
        if self.mistral_client:
            return self.mistral_client

        self.api_key = self.api_key or getenv("MISTRAL_API_KEY")
        if not self.api_key:
            logger.error("MISTRAL_API_KEY not set. Please set the MISTRAL_API_KEY environment variable.")

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.endpoint:
            _client_params["endpoint"] = self.endpoint
        if self.max_retries:
            _client_params["max_retries"] = self.max_retries
        if self.timeout:
            _client_params["timeout"] = self.timeout
        if self.client_params:
            _client_params.update(self.client_params)
        return Mistral(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        """
        Get the API kwargs for the Mistral model.

        Returns:
            Dict[str, Any]: The API kwargs.
        """
        _request_params: Dict[str, Any] = {}
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.random_seed:
            _request_params["random_seed"] = self.random_seed
        if self.safe_mode:
            _request_params["safe_mode"] = self.safe_mode
        if self.safe_prompt:
            _request_params["safe_prompt"] = self.safe_prompt
        if self.tools:
            _request_params["tools"] = self.get_tools_for_api()
            if self.tool_choice is None:
                _request_params["tool_choice"] = "auto"
            else:
                _request_params["tool_choice"] = self.tool_choice
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary.

        Returns:
            Dict[str, Any]: The dictionary representation of the model.
        """
        _dict = super().to_dict()
        if self.temperature:
            _dict["temperature"] = self.temperature
        if self.max_tokens:
            _dict["max_tokens"] = self.max_tokens
        if self.random_seed:
            _dict["random_seed"] = self.random_seed
        if self.safe_mode:
            _dict["safe_mode"] = self.safe_mode
        if self.safe_prompt:
            _dict["safe_prompt"] = self.safe_prompt
        if self.response_format:
            _dict["response_format"] = self.response_format
        return _dict

    def invoke(self, messages: List[Message]) -> ChatCompletionResponse:
        """
        Send a chat completion request to the Mistral model.

        Args:
            messages (List[Message]): The messages to send to the model.

        Returns:
            ChatCompletionResponse: The response from the model.
        """
        mistral_messages: List[MistralMessage] = []
        for m in messages:
            mistral_message: MistralMessage
            if m.role == "user":
                mistral_message = models.UserMessage(role=m.role, content=m.content)
            elif m.role == "assistant":
                if m.tool_calls is not None:
                    mistral_message = models.AssistantMessage(role=m.role, content=m.content, tool_calls=m.tool_calls)
                else:
                    mistral_message = models.AssistantMessage(role=m.role, content=m.content)
            elif m.role == "system":
                mistral_message = models.SystemMessage(role=m.role, content=m.content)
            elif m.role == "tool":
                mistral_message = models.ToolMessage(name=m.name, content=m.content, tool_call_id=m.tool_call_id)
            else:
                raise ValueError(f"Unknown role: {m.role}")
            mistral_messages.append(mistral_message)
        logger.debug(f"Mistral messages: {mistral_messages}")
        response = self.client.chat.complete(
            messages=mistral_messages,
            model=self.id,
            **self.api_kwargs,
        )
        if response is None:
            raise ValueError("Chat completion returned None")
        return response

    def invoke_stream(self, messages: List[Message]) -> Iterator[Any]:
        """
        Stream the response from the Mistral model.

        Args:
            messages (List[Message]): The messages to send to the model.

        Returns:
            Iterator[Any]: The streamed response.
        """
        mistral_messages: List[MistralMessage] = []
        for m in messages:
            mistral_message: MistralMessage
            if m.role == "user":
                mistral_message = models.UserMessage(role=m.role, content=m.content)
            elif m.role == "assistant":
                if m.tool_calls is not None:
                    mistral_message = models.AssistantMessage(role=m.role, content=m.content, tool_calls=m.tool_calls)
                else:
                    mistral_message = models.AssistantMessage(role=m.role, content=m.content)
            elif m.role == "system":
                mistral_message = models.SystemMessage(role=m.role, content=m.content)
            elif m.role == "tool":
                logger.debug(f"Tool message: {m}")
                mistral_message = models.ToolMessage(name=m.name, content=m.content, tool_call_id=m.tool_call_id)
            else:
                raise ValueError(f"Unknown role: {m.role}")
            mistral_messages.append(mistral_message)
        logger.debug(f"Mistral messages sending to stream endpoint: {mistral_messages}")
        response = self.client.chat.stream(
            messages=mistral_messages,
            model=self.id,
            **self.api_kwargs,
        )
        if response is None:
            raise ValueError("Chat stream returned None")
        # Since response is a generator, use 'yield from' to yield its items
        yield from response

    def _handle_tool_calls(
        self, assistant_message: Message, messages: List[Message], model_response: ModelResponse
    ) -> Optional[ModelResponse]:
        """
        Handle tool calls in the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): The messages to send to the model.
            model_response (ModelResponse): The model response.

        Returns:
            Optional[ModelResponse]: The model response after handling tool calls.
        """
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0:
            model_response.content = ""
            tool_role: str = "tool"
            function_calls_to_run: List[FunctionCall] = []
            function_call_results: List[Message] = []
            for tool_call in assistant_message.tool_calls:
                tool_call["type"] = "function"
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(role="tool", tool_call_id=_tool_call_id, content="Could not find function to call.")
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role="tool", tool_call_id=_tool_call_id, tool_call_error=True, content=_function_call.error
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    model_response.content += f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    model_response.content += "\nRunning:"
                    for _f in function_calls_to_run:
                        model_response.content += f"\n - {_f.get_call_str()}"
                    model_response.content += "\n\n"

            for _ in self.run_function_calls(
                function_calls=function_calls_to_run, function_call_results=function_call_results, tool_role=tool_role
            ):
                pass

            if len(function_call_results) > 0:
                messages.extend(function_call_results)

            return model_response
        return None

    def _create_assistant_message(self, response: ChatCompletionResponse) -> Message:
        """
        Create an assistant message from the response.

        Args:
            response (ChatCompletionResponse): The response from the model.

        Returns:
            Message: The assistant message.
        """
        if response.choices is None or len(response.choices) == 0:
            raise ValueError("The response does not contain any choices.")

        response_message: models.AssistantMessage = response.choices[0].message

        # Create assistant message
        assistant_message = Message(
            role=response_message.role or "assistant",
            content=response_message.content,
        )

        if isinstance(response_message.tool_calls, list) and len(response_message.tool_calls) > 0:
            assistant_message.tool_calls = [t.model_dump() for t in response_message.tool_calls]

        return assistant_message

    def _update_usage_metrics(
        self, assistant_message: Message, response: ChatCompletionResponse, response_timer: Timer
    ) -> None:
        """
        Update the usage metrics for the response.

        Args:
            assistant_message (Message): The assistant message.
            response (ChatCompletionResponse): The response from the model.
            response_timer (Timer): The timer for the response.
        """
        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)
        # Add token usage to metrics
        self.metrics.update(response.usage.model_dump())

    def _log_messages(self, messages: List[Message]) -> None:
        """
        Log messages for debugging.
        """
        for m in messages:
            m.log()

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Send a chat completion request to the Mistral model.

        Args:
            messages (List[Message]): The messages to send to the model.

        Returns:
            ModelResponse: The response from the model.
        """
        logger.debug("---------- Mistral Response Start ----------")
        # -*- Log messages for debugging
        self._log_messages(messages)
        model_response = ModelResponse()

        response_timer = Timer()
        response_timer.start()
        response: ChatCompletionResponse = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Ensure response.choices is not None
        if response.choices is None or len(response.choices) == 0:
            raise ValueError("Chat completion response has no choices")

        # -*- Create assistant message
        assistant_message = self._create_assistant_message(response)

        # -*- Update usage metrics
        self._update_usage_metrics(assistant_message, response, response_timer)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run tool calls
        logger.debug(f"Functions: {self.functions}")

        # -*- Handle tool calls
        if self._handle_tool_calls(assistant_message, messages, model_response):
            response_after_tool_calls = self.response(messages=messages)
            if response_after_tool_calls.content is not None:
                if model_response.content is None:
                    model_response.content = ""
                model_response.content += response_after_tool_calls.content
            return model_response

        # -*- Add content to model response
        if assistant_message.content is not None:
            model_response.content = assistant_message.get_content_string()

        logger.debug("---------- Mistral Response End ----------")
        return model_response

    def _update_stream_metrics(self, stream_data: StreamData, assistant_message: Message):
        """
        Update the metrics for the streaming response.

        Args:
            stream_data (StreamData): The streaming data
            assistant_message (Message): The assistant message.
        """
        assistant_message.metrics["time"] = stream_data.response_timer.elapsed
        if stream_data.time_to_first_token is not None:
            assistant_message.metrics["time_to_first_token"] = stream_data.time_to_first_token

        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(stream_data.response_timer.elapsed)
        if stream_data.time_to_first_token is not None:
            if "time_to_first_token" not in self.metrics:
                self.metrics["time_to_first_token"] = []
            self.metrics["time_to_first_token"].append(stream_data.time_to_first_token)

        assistant_message.metrics["prompt_tokens"] = stream_data.response_prompt_tokens
        assistant_message.metrics["input_tokens"] = stream_data.response_prompt_tokens
        self.metrics["prompt_tokens"] = self.metrics.get("prompt_tokens", 0) + stream_data.response_prompt_tokens
        self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + stream_data.response_prompt_tokens

        assistant_message.metrics["completion_tokens"] = stream_data.response_completion_tokens
        assistant_message.metrics["output_tokens"] = stream_data.response_completion_tokens
        self.metrics["completion_tokens"] = (
            self.metrics.get("completion_tokens", 0) + stream_data.response_completion_tokens
        )
        self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + stream_data.response_completion_tokens

        assistant_message.metrics["total_tokens"] = stream_data.response_total_tokens
        self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + stream_data.response_total_tokens

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        """
        Stream the response from the Mistral model.

        Args:
            messages (List[Message]): The messages to send to the model.

        Returns:
            Iterator[ModelResponse]: The streamed response.
        """
        logger.debug("---------- Mistral Response Start ----------")
        # -*- Log messages for debugging
        self._log_messages(messages)

        stream_data: StreamData = StreamData()
        stream_data.response_timer.start()

        assistant_message_role = None
        for response in self.invoke_stream(messages=messages):
            # -*- Parse response
            response_delta: DeltaMessage = response.data.choices[0].delta
            if assistant_message_role is None and response_delta.role is not None:
                assistant_message_role = response_delta.role

            response_content: Optional[str] = None
            if response_delta.content is not None and not isinstance(response_delta.content, Unset):
                response_content = response_delta.content
            response_tool_calls = response_delta.tool_calls

            # -*- Return content if present, otherwise get tool call
            if response_content is not None:
                stream_data.response_content += response_content
                stream_data.completion_tokens += 1
                if stream_data.completion_tokens == 1:
                    stream_data.time_to_first_token = stream_data.response_timer.elapsed
                    logger.debug(f"Time to first token: {stream_data.time_to_first_token:.4f}s")
                yield ModelResponse(content=response_content)

            # -*- Parse tool calls
            if response_tool_calls is not None:
                if stream_data.response_tool_calls is None:
                    stream_data.response_tool_calls = []
                stream_data.response_tool_calls.extend(response_tool_calls)

        stream_data.response_timer.stop()
        completion_tokens = stream_data.completion_tokens
        if completion_tokens > 0:
            logger.debug(f"Time per output token: {stream_data.response_timer.elapsed / completion_tokens:.4f}s")
            logger.debug(f"Throughput: {completion_tokens / stream_data.response_timer.elapsed:.4f} tokens/s")

        # -*- Create assistant message
        assistant_message = Message(role=(assistant_message_role or "assistant"))
        if stream_data.response_content != "":
            assistant_message.content = stream_data.response_content

        # -*- Add tool calls to assistant message
        if stream_data.response_tool_calls is not None:
            assistant_message.tool_calls = [t.model_dump() for t in stream_data.response_tool_calls]

        # -*- Update usage metrics
        self._update_stream_metrics(stream_data, assistant_message)
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0:
            tool_role: str = "tool"
            function_calls_to_run: List[FunctionCall] = []
            function_call_results: List[Message] = []

            for tool_call in assistant_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                tool_call["type"] = "function"
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(role="tool", tool_call_id=_tool_call_id, content="Could not find function to call.")
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role="tool", tool_call_id=_tool_call_id, tool_call_error=True, content=_function_call.error
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield ModelResponse(content=f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n")
                elif len(function_calls_to_run) > 1:
                    yield ModelResponse(content="\nRunning:")
                    for _f in function_calls_to_run:
                        yield ModelResponse(content=f"\n - {_f.get_call_str()}")
                    yield ModelResponse(content="\n\n")

            for intermediate_model_response in self.run_function_calls(
                function_calls=function_calls_to_run, function_call_results=function_call_results, tool_role=tool_role
            ):
                yield intermediate_model_response

            if len(function_call_results) > 0:
                messages.extend(function_call_results)

            yield from self.response_stream(messages=messages)
        logger.debug("---------- Mistral Response End ----------")
