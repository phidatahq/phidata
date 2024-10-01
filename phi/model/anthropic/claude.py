import json
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


class Claude(Model):
    """
    A class representing Anthropics Claude models.

    Claude models are designed to generate text based on a given input.

    Attributes:
        id (str): The id of the Anthropic Claude model to use. Defaults to "claude-3-5-sonnet-2024062".
        name (str): The name of the model. Defaults to "claude".
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

    id: str = "claude-3-5-sonnet-20240620"
    name: str = "claude"

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

    def _process_messages(self, messages: List[Message]) -> Tuple[List[Dict[str, str]], str]:
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
                chat_messages.append({"role": message.role, "content": content}) # type: ignore

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
        chat_messages, system_message = self._process_messages(messages)
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
        chat_messages, system_message = self._process_messages(messages)
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

    def _update_usage_metrics(self, assistant_message: Message, usage: Optional[Usage]) -> None:
        """
        Update the usage metrics for the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            usage (Optional[Usage]): The usage metrics.
        """
        if usage:
            input_tokens = usage.input_tokens or 0
            output_tokens = usage.output_tokens or 0
            total_tokens = input_tokens + output_tokens

            if input_tokens is not None:
                assistant_message.metrics["input_tokens"] = input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + input_tokens
            if output_tokens is not None:
                assistant_message.metrics["output_tokens"] = output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + output_tokens
            if total_tokens is not None:
                assistant_message.metrics["total_tokens"] = total_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + total_tokens

    def _create_assistant_message(
        self, response: AnthropicMessage, response_timer: Timer, response_usage: Optional[Usage]
    ) -> Tuple[Message, str, List[str]]:
        """
        Create an assistant message from the response.

        Args:
            response (AnthropicMessage): The response from the model.
            response_timer (Timer): The timer for the response.
            response_usage (Optional[Usage]): The usage metrics for the response.

        Returns:
            Tuple[Message, str, List[str]]: A tuple containing the assistant message, the response content, and the tool ids.
        """
        response_content: str = ""
        response_block: Optional[Union[TextBlock, ToolUseBlock]] = None
        tool_calls: List[Dict[str, Any]] = []
        tool_ids: List[str] = []

        if response.content:
            response_block = response.content[0]

        if response_block is not None:
            if isinstance(response_block, TextBlock):
                response_content = response_block.text
            elif isinstance(response_block, ToolUseBlock):
                tool_block_input = response_block.input
                if tool_block_input and isinstance(tool_block_input, dict):
                    response_content = tool_block_input.get("query", "")

        assistant_message = Message(
            role=response.role or "assistant",
            content=response_content,
        )

        if response.stop_reason == "tool_use":
            for block in response.content:
                if isinstance(block, ToolUseBlock):
                    tool_use: ToolUseBlock = block
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    tool_ids.append(tool_use.id)

                    function_def = {"name": tool_name}
                    if tool_input:
                        function_def["arguments"] = json.dumps(tool_input)
                    tool_calls.append(
                        {
                            "type": "function",
                            "function": function_def,
                        }
                    )

            if len(tool_calls) > 0:
                assistant_message.tool_calls = tool_calls
                assistant_message.content = response.content

        # Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        self.metrics.setdefault("response_times", []).append(response_timer.elapsed)
        self._update_usage_metrics(assistant_message, response_usage)

        return assistant_message, response_content, tool_ids

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
            function_calls_to_run: List[FunctionCall] = []
            function_call_results: List[Message] = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="user", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="user", content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

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
        # Log messages for debugging
        self._log_messages(messages)

        # Create a ModelResponse object to return
        model_response = ModelResponse()

        response_timer = Timer()
        response_timer.start()
        response: AnthropicMessage = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # Create assistant message
        assistant_message, response_content, tool_ids = self._create_assistant_message(
            response, response_timer, response.usage
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

    def _handle_tool_calls_stream(
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
            function_calls_to_run: List[FunctionCall] = []
            function_call_results: List[Message] = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="user", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="user", content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield ModelResponse(content=f" - Running: {function_calls_to_run[0].get_call_str()}\n\n")
                elif len(function_calls_to_run) > 1:
                    yield ModelResponse(content="Running:")
                    for _f in function_calls_to_run:
                        yield ModelResponse(content="\n - {_f.get_call_str()}")
                    yield ModelResponse(content="\n\n")

            for intermediate_model_response in self.run_function_calls(
                function_calls=function_calls_to_run, function_call_results=function_call_results
            ):
                yield intermediate_model_response

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

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        logger.debug("---------- Claude Response Start ----------")
        # -*- Log messages for debugging
        self._log_messages(messages)

        response_content_text: str = ""
        response_content: List[Optional[Union[TextBlock, ToolUseBlock]]] = []
        response_usage: Optional[Usage] = None
        tool_calls: List[Dict[str, Any]] = []
        tool_ids: List[str] = []
        response_timer = Timer()
        response_timer.start()
        response = self.invoke_stream(messages=messages)
        with response as stream:
            for delta in stream:
                if isinstance(delta, RawContentBlockDeltaEvent):
                    if isinstance(delta.delta, TextDelta):
                        yield ModelResponse(content=delta.delta.text)
                        response_content_text += delta.delta.text

                if isinstance(delta, ContentBlockStopEvent):
                    if isinstance(delta.content_block, ToolUseBlock):
                        tool_use = delta.content_block
                        tool_name = tool_use.name
                        tool_input = tool_use.input
                        tool_ids.append(tool_use.id)

                        function_def = {"name": tool_name}
                        if tool_input:
                            function_def["arguments"] = json.dumps(tool_input)
                        tool_calls.append(
                            {
                                "type": "function",
                                "function": function_def,
                            }
                        )
                    response_content.append(delta.content_block)

                if isinstance(delta, MessageStopEvent):
                    response_usage = delta.message.usage
        yield ModelResponse(content="\n\n")

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response_content_text,
        )

        if len(tool_calls) > 0:
            assistant_message.content = response_content
            assistant_message.tool_calls = tool_calls

        # Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        self.metrics.setdefault("response_times", []).append(response_timer.elapsed)
        self._update_usage_metrics(assistant_message, response_usage)

        messages.append(assistant_message)
        assistant_message.log()

        yield from self._handle_tool_calls_stream(assistant_message, messages, tool_ids)

        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            yield from self.response_stream(messages=messages)

        logger.debug("---------- Claude Response End ----------")

    def get_tool_call_prompt(self) -> Optional[str]:
        if self.functions is not None and len(self.functions) > 0:
            tool_call_prompt = "Do not reflect on the quality of the returned search results in your response"
            return tool_call_prompt
        return None

    def get_system_prompt_from_model(self) -> Optional[str]:
        return self.get_tool_call_prompt()
