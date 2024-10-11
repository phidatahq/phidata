from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Union

import httpx

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from groq import Groq as GroqClient
    from groq.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
except ImportError:
    logger.error("`groq` not installed")
    raise


@dataclass
class StreamData:
    response_content: str = ""
    response_tool_calls: Optional[List[ChoiceDeltaToolCall]] = None
    completion_tokens: int = 0
    response_prompt_tokens: int = 0
    response_completion_tokens: int = 0
    response_total_tokens: int = 0
    time_to_first_token: Optional[float] = None
    response_timer: Timer = field(default_factory=Timer)


class Groq(Model):
    """
    Groq model class.

    Args:
        id (str): The model ID.
        name (str): The model name.
        provider (str): The model provider.
        frequency_penalty (float): The frequency penalty.
        logit_bias (dict): The logit bias.
        logprobs (bool): The logprobs.
        max_tokens (int): The maximum tokens.
        presence_penalty (float): The presence penalty.
        response_format (dict): The response format.
        seed (int): The seed.
        stop (str or list): The stop.
        temperature (float): The temperature.
        top_logprobs (int): The top logprobs.
        top_p (float): The top p.
        user (str): The user.
        extra_headers (dict): The extra headers.
        extra_query (dict): The extra query.
        request_params (dict): The request parameters.
        api_key (str): The API key.
        base_url (str): The base URL.
        timeout (int): The timeout.
        max_retries (int): The maximum retries.
        default_headers (dict): The default headers.
        default_query (dict): The default query.
        client_params (dict): The client parameters.
        groq_client (GroqClient): The Groq client.
    """

    id: str = "llama3-groq-70b-8192-tool-use-preview"
    name: str = "Groq"
    provider: str = "Groq"

    # -*- Request parameters
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
    # -*- Client parameters
    api_key: Optional[str] = None
    base_url: Optional[Union[str, httpx.URL]] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    default_headers: Optional[Any] = None
    default_query: Optional[Any] = None
    client_params: Optional[Dict[str, Any]] = None
    # -*- Provide the Groq manually
    groq_client: Optional[GroqClient] = None

    @property
    def client(self) -> GroqClient:
        """
        Get the Groq client.

        Returns:
            GroqClient: The Groq client.
        """
        if self.groq_client:
            return self.groq_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.base_url:
            _client_params["base_url"] = self.base_url
        if self.timeout:
            _client_params["timeout"] = self.timeout
        if self.max_retries:
            _client_params["max_retries"] = self.max_retries
        if self.default_headers:
            _client_params["default_headers"] = self.default_headers
        if self.default_query:
            _client_params["default_query"] = self.default_query
        if self.client_params:
            _client_params.update(self.client_params)
        return GroqClient(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        """
        Get the API kwargs.

        Returns:
            Dict[str, Any]: The API kwargs.
        """
        _request_params: Dict[str, Any] = {}
        if self.frequency_penalty:
            _request_params["frequency_penalty"] = self.frequency_penalty
        if self.logit_bias:
            _request_params["logit_bias"] = self.logit_bias
        if self.logprobs:
            _request_params["logprobs"] = self.logprobs
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.presence_penalty:
            _request_params["presence_penalty"] = self.presence_penalty
        if self.response_format:
            _request_params["response_format"] = self.response_format
        if self.seed:
            _request_params["seed"] = self.seed
        if self.stop:
            _request_params["stop"] = self.stop
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.top_logprobs:
            _request_params["top_logprobs"] = self.top_logprobs
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.user:
            _request_params["user"] = self.user
        if self.extra_headers:
            _request_params["extra_headers"] = self.extra_headers
        if self.extra_query:
            _request_params["extra_query"] = self.extra_query
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
        Get the dictionary representation of the model.

        Returns:
            Dict[str, Any]: The dictionary representation of the model.
        """
        _dict = super().to_dict()
        if self.frequency_penalty:
            _dict["frequency_penalty"] = self.frequency_penalty
        if self.logit_bias:
            _dict["logit_bias"] = self.logit_bias
        if self.logprobs:
            _dict["logprobs"] = self.logprobs
        if self.max_tokens:
            _dict["max_tokens"] = self.max_tokens
        if self.presence_penalty:
            _dict["presence_penalty"] = self.presence_penalty
        if self.response_format:
            _dict["response_format"] = self.response_format
        if self.seed:
            _dict["seed"] = self.seed
        if self.stop:
            _dict["stop"] = self.stop
        if self.temperature:
            _dict["temperature"] = self.temperature
        if self.top_logprobs:
            _dict["top_logprobs"] = self.top_logprobs
        if self.top_p:
            _dict["top_p"] = self.top_p
        if self.user:
            _dict["user"] = self.user
        if self.extra_headers:
            _dict["extra_headers"] = self.extra_headers
        if self.extra_query:
            _dict["extra_query"] = self.extra_query
        if self.tools:
            _dict["tools"] = self.get_tools_for_api()
            if self.tool_choice is None:
                _dict["tool_choice"] = "auto"
            else:
                _dict["tool_choice"] = self.tool_choice
        return _dict

    def invoke(self, messages: List[Message]) -> Any:
        """
        Invoke the Groq model.

        Args:
            messages (List[Message]): The messages.

        Returns:
            Any: The response.
        """
        if self.tools and self.response_format:
            logger.warning(
                f"Response format is not supported for Groq when specifying tools. Ignoring response_format: {self.response_format}"
            )
            self.response_format = {"type": "text"}
        return self.client.chat.completions.create(
            model=self.id,
            messages=[m.to_dict() for m in messages],  # type: ignore
            **self.api_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Iterator[Any]:
        """
        Invoke the Groq model stream.

        Args:
            messages (List[Message]): The messages.

        Returns:
            Iterator[Any]: The response.
        """
        yield from self.client.chat.completions.create(
            model=self.id,
            messages=[m.to_dict() for m in messages],  # type: ignore
            stream=True,
            **self.api_kwargs,
        )

    def _log_messages(self, messages: List[Message]) -> None:
        """
        Log the messages.

        Args:
            messages (List[Message]): The messages.
        """
        for m in messages:
            m.log()

    def _create_assistant_message(self, response: Any) -> Message:
        """
        Create the assistant message.

        Args:
            response (Any): The response.

        Returns:
            Message: The assistant message.
        """
        response_message = response.choices[0].message
        assistant_message = Message(
            role=response_message.role or "assistant",
            content=response_message.content,
        )
        if response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            assistant_message.tool_calls = [t.model_dump() for t in response_message.tool_calls]
        return assistant_message

    def _update_usage_metrics(
        self,
        assistant_message: Message,
        response_timer_elapsed: float,
        response_usage: Any,
    ) -> None:
        """
        Update the usage metrics.

        Args:
            assistant_message (Message): The assistant message.
            response_timer_elapsed (float): The response timer elapsed.
            response_usage (Any): The response usage.
        """
        assistant_message.metrics["time"] = response_timer_elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer_elapsed)
        if response_usage is not None:
            self.metrics.update(response_usage.model_dump())

    def _handle_tool_calls(
        self,
        assistant_message: Message,
        messages: List[Message],
        model_response: ModelResponse,
    ) -> Optional[ModelResponse]:
        """
        Handle the tool calls.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): The messages.
            model_response (ModelResponse): The model response.

        Returns:
            Optional[ModelResponse]: The model response.
        """
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0:
            model_response.content = ""
            tool_role: str = "tool"
            function_call_results: List[Message] = []
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content="Could not find function to call.",
                        )
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role="tool",
                            tool_call_id=_tool_call_id,
                            content=_function_call.error,
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                model_response.content += "\nRunning:"
                for _f in function_calls_to_run:
                    model_response.content += f"\n - {_f.get_call_str()}"
                model_response.content += "\n\n"

            for _ in self.run_function_calls(
                function_calls=function_calls_to_run,
                function_call_results=function_call_results,
                tool_role=tool_role,
            ):
                pass

            if len(function_call_results) > 0:
                messages.extend(function_call_results)

            return model_response
        return None

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Response the Groq model.

        Args:
            messages (List[Message]): The messages.

        Returns:
            ModelResponse: The model response.
        """
        logger.debug("---------- Groq Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        response_timer = Timer()
        response_timer.start()
        response = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        assistant_message = self._create_assistant_message(response)
        self._update_usage_metrics(assistant_message, response_timer.elapsed, response.usage)

        messages.append(assistant_message)
        assistant_message.log()

        if self._handle_tool_calls(assistant_message, messages, model_response):
            response_after_tool_calls = self.response(messages=messages)
            if response_after_tool_calls.content is not None:
                if model_response.content is None:
                    model_response.content = ""
                model_response.content += response_after_tool_calls.content
            return model_response

        logger.debug("---------- Groq Response End ----------")
        if assistant_message.content is not None:
            model_response.content = assistant_message.get_content_string()

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
            assistant_message.metrics["time_to_first_token"] = f"{stream_data.time_to_first_token:.4f}s"
        if stream_data.completion_tokens > 0:
            assistant_message.metrics["time_per_output_token"] = (
                f"{stream_data.response_timer.elapsed / stream_data.completion_tokens:.4f}s"
            )

        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(stream_data.response_timer.elapsed)
        if stream_data.time_to_first_token is not None:
            if "time_to_first_token" not in self.metrics:
                self.metrics["time_to_first_token"] = []
            self.metrics["time_to_first_token"].append(f"{stream_data.time_to_first_token:.4f}s")
        if stream_data.completion_tokens > 0:
            if "tokens_per_second" not in self.metrics:
                self.metrics["tokens_per_second"] = []
            self.metrics["tokens_per_second"].append(
                f"{stream_data.completion_tokens / stream_data.response_timer.elapsed:.4f}"
            )

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
        Response the Groq model stream.

        Args:
            messages (List[Message]): The messages.

        Returns:
            Iterator[ModelResponse]: The model response.
        """
        logger.debug("---------- Groq Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        stream_data: StreamData = StreamData()
        stream_data.response_timer.start()

        for response in self.invoke_stream(messages=messages):
            # -*- Parse response
            response_delta = response.choices[0].delta
            response_content: Optional[str] = response_delta.content
            response_tool_calls: Optional[List[Any]] = response_delta.tool_calls

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

            if response.usage:
                response_usage: Optional[Any] = response.usage
                if response_usage:
                    stream_data.response_prompt_tokens = response_usage.prompt_tokens
                    stream_data.response_completion_tokens = response_usage.completion_tokens
                    stream_data.response_total_tokens = response_usage.total_tokens

        stream_data.response_timer.stop()
        completion_tokens = stream_data.completion_tokens
        if completion_tokens > 0:
            logger.debug(f"Time per output token: {stream_data.response_timer.elapsed / completion_tokens:.4f}s")
            logger.debug(f"Throughput: {completion_tokens / stream_data.response_timer.elapsed:.4f} tokens/s")

        # -*- Create assistant message
        assistant_message = Message(role="assistant")
        if stream_data.response_content != "":
            assistant_message.content = stream_data.response_content

        # -*- Add tool calls to assistant message
        if stream_data.response_tool_calls is not None:
            assistant_message.tool_calls = [t.model_dump() for t in stream_data.response_tool_calls]

        # -*- Update usage metrics
        # Add response time to metrics
        self._update_stream_metrics(stream_data=stream_data, assistant_message=assistant_message)
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            tool_role: str = "tool"
            function_calls_to_run: List[FunctionCall] = []
            function_call_results: List[Message] = []
            for tool_call in assistant_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(
                            role=tool_role,
                            tool_call_id=_tool_call_id,
                            content="Could not find function to call.",
                        )
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(
                        Message(
                            role=tool_role,
                            tool_call_id=_tool_call_id,
                            content=_function_call.error,
                        )
                    )
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
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
        logger.debug("---------- Groq Response End ----------")
