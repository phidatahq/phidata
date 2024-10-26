import json
from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Union, Tuple

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import (
    get_function_call_for_tool_call,
)

try:
    from anthropic import Anthropic as AnthropicClient
    from anthropic.types import Message as AnthropicMessage, TextBlock, ToolUseBlock, Usage, TextDelta
    from anthropic.lib.streaming._types import (
        MessageStopEvent,
        RawContentBlockDeltaEvent,
        ContentBlockStopEvent,
    )
except ImportError:
    logger.error("`anthropic` not installed")
    raise


@dataclass
class MessageData:
    response_content: str = ""
    response_block: List[Union[TextBlock, ToolUseBlock]] = field(default_factory=list)
    response_block_content: Optional[Union[TextBlock, ToolUseBlock]] = None
    response_usage: Optional[Usage] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_ids: List[str] = field(default_factory=list)


@dataclass
class UsageData:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class StreamUsageData:
    completion_tokens: int = 0
    time_to_first_token: Optional[float] = None
    tokens_per_second: Optional[float] = None
    time_per_token: Optional[float] = None


class Claude(Model):
    """
    A class representing Anthropic Claude model.


    This class provides an interface for interacting with the Anthropic Claude model.

    Attributes:
        id (str): The id of the Anthropic Claude model to use. Defaults to "claude-3-5-sonnet-2024062".
        name (str): The name of the model. Defaults to "Claude".
        provider (str): The provider of the model. Defaults to "Anthropic".
        max_tokens (Optional[int]): The maximum number of tokens to generate in the chat completion.
        temperature (Optional[float]): Controls randomness in the model's output.
        stop_sequences (Optional[List[str]]): A list of strings that the model should stop generating text at.
        top_p (Optional[float]): Controls diversity via nucleus sampling.
        top_k (Optional[int]): Controls diversity via top-k sampling.
        request_params (Optional[Dict[str, Any]]): Additional parameters to include in the request.
        api_key (Optional[str]): The API key for authenticating with Anthropic.
        client_params (Optional[Dict[str, Any]]): Additional parameters for client configuration.
        client (Optional[AnthropicClient]): A pre-configured instance of the Anthropic client.
    """

    id: str = "claude-3-5-sonnet-20241022"
    name: str = "Claude"
    provider: str = "Anthropic"

    # Request parameters
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    request_params: Optional[Dict[str, Any]] = None

    # Client parameters
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None

    # Anthropic client
    client: Optional[AnthropicClient] = None

    def get_client(self) -> AnthropicClient:
        """
        Returns an instance of the Anthropic client.

        Returns:
            AnthropicClient: An instance of the Anthropic client
        """
        if self.client:
            return self.client

        _client_params: Dict[str, Any] = {}
        # Set client parameters if they are provided
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.client_params:
            _client_params.update(self.client_params)
        return AnthropicClient(**_client_params)

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """
        Generate keyword arguments for API requests.

        Returns:
            Dict[str, Any]: A dictionary of keyword arguments for API requests.
        """
        _request_params: Dict[str, Any] = {}
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.stop_sequences:
            _request_params["stop_sequences"] = self.stop_sequences
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.top_k:
            _request_params["top_k"] = self.top_k
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def _format_messages(self, messages: List[Message]) -> Tuple[List[Dict[str, str]], str]:
        """
        Process the list of messages and separate them into API messages and system messages.

        Args:
            messages (List[Message]): The list of messages to process.

        Returns:
            Tuple[List[Dict[str, str]], str]: A tuple containing the list of API messages and the concatenated system messages.
        """
        chat_messages: List[Dict[str, str]] = []
        system_messages: List[str] = []

        for idx, message in enumerate(messages):
            content = message.content or ""
            if message.role == "system" or (message.role != "user" and idx in [0, 1]):
                system_messages.append(content)  # type: ignore
            else:
                chat_messages.append({"role": message.role, "content": content})  # type: ignore
        return chat_messages, " ".join(system_messages)

    def _prepare_request_kwargs(self, system_message: str) -> Dict[str, Any]:
        """
        Prepare the request keyword arguments for the API call.

        Args:
            system_message (str): The concatenated system messages.

        Returns:
            Dict[str, Any]: The request keyword arguments.
        """
        request_kwargs = self.request_kwargs.copy()
        request_kwargs["system"] = system_message

        if self.tools:
            request_kwargs["tools"] = self._get_tools()
        return request_kwargs

    def _get_tools(self) -> Optional[List[Dict[str, Any]]]:
        """
        Transforms function definitions into a format accepted by the Anthropic API.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of tools formatted for the API, or None if no functions are defined.
        """
        if not self.functions:
            return None

        tools: List[Dict[str, Any]] = []
        for func_name, func_def in self.functions.items():
            parameters: Dict[str, Any] = func_def.parameters or {}
            properties: Dict[str, Any] = parameters.get("properties", {})
            required_params: List[str] = []

            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "")
                param_type_list: List[str] = [param_type] if isinstance(param_type, str) else param_type or []

                if "null" not in param_type_list:
                    required_params.append(param_name)

            input_properties: Dict[str, Dict[str, Union[str, List[str]]]] = {
                param_name: {
                    "type": param_info.get("type", ""),
                    "description": param_info.get("description", ""),
                }
                for param_name, param_info in properties.items()
            }

            tool = {
                "name": func_name,
                "description": func_def.description or "",
                "input_schema": {
                    "type": parameters.get("type", "object"),
                    "properties": input_properties,
                    "required": required_params,
                },
            }
            tools.append(tool)
        return tools

    def invoke(self, messages: List[Message]) -> AnthropicMessage:
        """
        Send a request to the Anthropic API to generate a response.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            AnthropicMessage: The response from the model.
        """
        chat_messages, system_message = self._format_messages(messages)
        request_kwargs = self._prepare_request_kwargs(system_message)

        return self.get_client().messages.create(
            model=self.id,
            messages=chat_messages,  # type: ignore
            **request_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Any:
        """
        Stream a response from the Anthropic API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Any: The streamed response from the model.
        """
        chat_messages, system_message = self._format_messages(messages)
        request_kwargs = self._prepare_request_kwargs(system_message)

        return self.get_client().messages.stream(
            model=self.id,
            messages=chat_messages,  # type: ignore
            **request_kwargs,
        )

    def _log_messages(self, messages: List[Message]) -> None:
        """
        Log messages for debugging.
        """
        for m in messages:
            m.log()

    def _update_usage_metrics(
        self,
        assistant_message: Message,
        usage: Optional[Usage] = None,
        stream_usage: Optional[StreamUsageData] = None,
    ) -> None:
        """
        Update the usage metrics for the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            usage (Optional[Usage]): The usage metrics.
            stream_usage (Optional[StreamUsageData]): The stream usage metrics.
        """
        if usage:
            usage_data = UsageData()
            usage_data.input_tokens = usage.input_tokens or 0
            usage_data.output_tokens = usage.output_tokens or 0
            usage_data.total_tokens = usage_data.input_tokens + usage_data.output_tokens

            if usage_data.input_tokens is not None:
                assistant_message.metrics["input_tokens"] = usage_data.input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + usage_data.input_tokens
            if usage_data.output_tokens is not None:
                assistant_message.metrics["output_tokens"] = usage_data.output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + usage_data.output_tokens
            if usage_data.total_tokens is not None:
                assistant_message.metrics["total_tokens"] = usage_data.total_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + usage_data.total_tokens

            if stream_usage:
                if stream_usage.time_to_first_token is not None:
                    assistant_message.metrics["time_to_first_token"] = stream_usage.time_to_first_token
                    self.metrics.setdefault("time_to_first_token", []).append(stream_usage.time_to_first_token)
                if stream_usage.tokens_per_second is not None:
                    assistant_message.metrics["tokens_per_second"] = stream_usage.tokens_per_second
                    self.metrics.setdefault("tokens_per_second", []).append(stream_usage.tokens_per_second)
                if stream_usage.time_per_token is not None:
                    assistant_message.metrics["time_per_token"] = stream_usage.time_per_token
                    self.metrics.setdefault("time_per_token", []).append(stream_usage.time_per_token)

    def _create_assistant_message(
        self, response: AnthropicMessage, response_timer: Timer
    ) -> Tuple[Message, str, List[str]]:
        """
        Create an assistant message from the response.

        Args:
            response (AnthropicMessage): The response from the model.
            response_timer (Timer): The timer for the response.

        Returns:
            Tuple[Message, str, List[str]]: A tuple containing the assistant message, the response content, and the tool ids.
        """
        message_data = MessageData()

        if response.content:
            message_data.response_block = response.content
            message_data.response_block_content = response.content[0]
            message_data.response_usage = response.usage

        # Extract response content
        if message_data.response_block_content is not None:
            if isinstance(message_data.response_block_content, TextBlock):
                message_data.response_content = message_data.response_block_content.text
            elif isinstance(message_data.response_block_content, ToolUseBlock):
                tool_block_input = message_data.response_block_content.input
                if tool_block_input and isinstance(tool_block_input, dict):
                    message_data.response_content = tool_block_input.get("query", "")

        # Create assistant message
        assistant_message = Message(
            role=response.role or "assistant",
            content=message_data.response_content,
        )

        # Extract tool calls from the response
        if response.stop_reason == "tool_use":
            for block in message_data.response_block:
                if isinstance(block, ToolUseBlock):
                    tool_use: ToolUseBlock = block
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    message_data.tool_ids.append(tool_use.id)

                    function_def = {"name": tool_name}
                    if tool_input:
                        function_def["arguments"] = json.dumps(tool_input)
                    message_data.tool_calls.append(
                        {
                            "type": "function",
                            "function": function_def,
                        }
                    )

        # Update assistant message if tool calls are present
        if len(message_data.tool_calls) > 0:
            assistant_message.tool_calls = message_data.tool_calls
            assistant_message.content = message_data.response_block

        # Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        self.metrics.setdefault("response_times", []).append(response_timer.elapsed)
        self._update_usage_metrics(assistant_message, message_data.response_usage)

        return assistant_message, message_data.response_content, message_data.tool_ids

    def _get_function_calls_to_run(self, assistant_message: Message, messages: List[Message]) -> List[FunctionCall]:
        """
        Prepare function calls for the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): The list of conversation messages.

        Returns:
            List[FunctionCall]: A list of function calls to run.
        """
        function_calls_to_run: List[FunctionCall] = []
        if assistant_message.tool_calls is not None:
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="user", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="user", content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)
        return function_calls_to_run

    def _format_function_call_results(
        self, function_call_results: List[Message], tool_ids: List[str], messages: List[Message]
    ) -> None:
        """
        Handle the results of function calls.

        Args:
            function_call_results (List[Message]): The results of the function calls.
            tool_ids (List[str]): The tool ids.
            messages (List[Message]): The list of conversation messages.
        """
        if len(function_call_results) > 0:
            fc_responses: List = []
            for _fc_message_index, _fc_message in enumerate(function_call_results):
                fc_responses.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_ids[_fc_message_index],
                        "content": _fc_message.content,
                    }
                )
            messages.append(Message(role="user", content=fc_responses))

    def _handle_tool_calls(
        self,
        assistant_message: Message,
        messages: List[Message],
        model_response: ModelResponse,
        response_content: str,
        tool_ids: List[str],
    ) -> Optional[ModelResponse]:
        """
        Handle tool calls in the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): A list of messages.
            model_response [ModelResponse]: The model response.
            response_content (str): The response content.
            tool_ids (List[str]): The tool ids.

        Returns:
            Optional[ModelResponse]: The model response.
        """
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            model_response.content = str(response_content)
            model_response.content += "\n\n"
            function_calls_to_run = self._get_function_calls_to_run(assistant_message, messages)
            function_call_results: List[Message] = []

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    model_response.content += f" - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    model_response.content += "Running:"
                    for _f in function_calls_to_run:
                        model_response.content += f"\n - {_f.get_call_str()}"
                    model_response.content += "\n\n"

            for _ in self.run_function_calls(
                function_calls=function_calls_to_run,
                function_call_results=function_call_results,
            ):
                pass

            self._format_function_call_results(function_call_results, tool_ids, messages)

            return model_response
        return None

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Send a chat completion request to the Anthropic API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            ModelResponse: The response from the model.
        """
        logger.debug("---------- Claude Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()

        response_timer = Timer()
        response_timer.start()
        response: AnthropicMessage = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # Create assistant message
        assistant_message, response_content, tool_ids = self._create_assistant_message(
            response=response,
            response_timer=response_timer,
        )
        messages.append(assistant_message)
        assistant_message.log()

        if self._handle_tool_calls(assistant_message, messages, model_response, response_content, tool_ids):
            response_after_tool_calls = self.response(messages=messages)
            if response_after_tool_calls.content is not None:
                if model_response.content is None:
                    model_response.content = ""
                model_response.content += response_after_tool_calls.content
            return model_response

        if assistant_message.content is not None:
            model_response.content = assistant_message.get_content_string()

        logger.debug("---------- Claude Response End ----------")
        return model_response

    def _handle_stream_tool_calls(
        self,
        assistant_message: Message,
        messages: List[Message],
        tool_ids: List[str],
    ) -> Iterator[ModelResponse]:
        """
        Parse and run function calls from the assistant message.

        Args:
            assistant_message (Message): The assistant message containing tool calls.
            messages (List[Message]): The list of conversation messages.
            tool_ids (List[str]): The list of tool IDs.

        Yields:
            Iterator[ModelResponse]: Yields model responses during function execution.
        """
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            yield ModelResponse(content="\n\n")
            function_calls_to_run = self._get_function_calls_to_run(assistant_message, messages)
            function_call_results: List[Message] = []

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield ModelResponse(content=f" - Running: {function_calls_to_run[0].get_call_str()}\n\n")
                elif len(function_calls_to_run) > 1:
                    yield ModelResponse(content="Running:")
                    for _f in function_calls_to_run:
                        yield ModelResponse(content=f"\n - {_f.get_call_str()}")
                    yield ModelResponse(content="\n\n")

            for intermediate_model_response in self.run_function_calls(
                function_calls=function_calls_to_run, function_call_results=function_call_results
            ):
                yield intermediate_model_response

            self._format_function_call_results(function_call_results, tool_ids, messages)

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        logger.debug("---------- Claude Response Start ----------")
        self._log_messages(messages)
        message_data = MessageData()
        stream_usage_data = StreamUsageData()

        response_timer = Timer()
        response_timer.start()
        response = self.invoke_stream(messages=messages)
        with response as stream:
            for delta in stream:
                if isinstance(delta, RawContentBlockDeltaEvent):
                    if isinstance(delta.delta, TextDelta):
                        yield ModelResponse(content=delta.delta.text)
                        message_data.response_content += delta.delta.text
                        stream_usage_data.completion_tokens += 1
                        if stream_usage_data.completion_tokens == 1:
                            stream_usage_data.time_to_first_token = response_timer.elapsed
                            logger.debug(f"Time to first token: {stream_usage_data.time_to_first_token:.4f}s")

                if isinstance(delta, ContentBlockStopEvent):
                    if isinstance(delta.content_block, ToolUseBlock):
                        tool_use = delta.content_block
                        tool_name = tool_use.name
                        tool_input = tool_use.input
                        message_data.tool_ids.append(tool_use.id)

                        function_def = {"name": tool_name}
                        if tool_input:
                            function_def["arguments"] = json.dumps(tool_input)
                        message_data.tool_calls.append(
                            {
                                "type": "function",
                                "function": function_def,
                            }
                        )
                    message_data.response_block.append(delta.content_block)

                if isinstance(delta, MessageStopEvent):
                    message_data.response_usage = delta.message.usage
        yield ModelResponse(content="\n\n")

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        if stream_usage_data.completion_tokens > 0:
            stream_usage_data.tokens_per_second = stream_usage_data.completion_tokens / response_timer.elapsed
            stream_usage_data.time_per_token = response_timer.elapsed / stream_usage_data.completion_tokens
            logger.debug(f"Tokens per second: {stream_usage_data.tokens_per_second:.4f}")
            logger.debug(f"Time per token: {stream_usage_data.time_per_token:.4f}s")

        # Create assistant message
        assistant_message = Message(
            role="assistant",
            content=message_data.response_content,
        )

        # Update assistant message if tool calls are present
        if len(message_data.tool_calls) > 0:
            assistant_message.content = message_data.response_block
            assistant_message.tool_calls = message_data.tool_calls

        # Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        self.metrics.setdefault("response_times", []).append(response_timer.elapsed)
        self._update_usage_metrics(assistant_message, message_data.response_usage, stream_usage=stream_usage_data)

        messages.append(assistant_message)
        assistant_message.log()

        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            yield from self._handle_stream_tool_calls(assistant_message, messages, message_data.tool_ids)
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Claude Response End ----------")

    def get_tool_call_prompt(self) -> Optional[str]:
        if self.functions is not None and len(self.functions) > 0:
            tool_call_prompt = "Do not reflect on the quality of the returned search results in your response"
            return tool_call_prompt
        return None

    def get_system_message_for_model(self) -> Optional[str]:
        return self.get_tool_call_prompt()
