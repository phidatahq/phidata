import json

from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Mapping, Union, Tuple

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from ollama import Client as OllamaClient, AsyncClient as AsyncOllamaClient
except ImportError:
    logger.error("`ollama` not installed")
    raise


@dataclass
class Metrics:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    time_to_first_token: Optional[float] = None
    response_timer: Timer = field(default_factory=Timer)

    def log(self):
        logger.debug("**************** METRICS START ****************")
        if self.time_to_first_token is not None:
            logger.debug(f"* Time to first token:         {self.time_to_first_token:.4f}s")
        logger.debug(f"* Time to generate response:   {self.response_timer.elapsed:.4f}s")
        logger.debug(f"* Tokens per second:           {self.output_tokens / self.response_timer.elapsed:.4f} tokens/s")
        logger.debug(f"* Input tokens:                {self.input_tokens}")
        logger.debug(f"* Output tokens:               {self.output_tokens}")
        logger.debug(f"* Total tokens:                {self.total_tokens}")
        logger.debug("**************** METRICS END ******************")


@dataclass
class MessageData:
    response_role: Optional[str] = None
    response_message: Optional[Dict[str, Any]] = None
    response_content: Any = ""
    response_content_chunk: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_blocks: Any = field(default_factory=list)
    tool_call_chunk: str = ""
    in_tool_call: bool = False
    response_usage: Optional[Mapping[str, Any]] = None


class Ollama(Model):
    """
    A class for interacting with Ollama models.

    Attributes:
        id (str): The ID of the model to use. Default is "llama3.2".
        name (str): The name of the model. Default is "Ollama".
        provider (str): The provider of the model. Default is "Ollama: llama3.2".
        format Optional[str]: The format of the response. Default is None.
        options Optional[Any]: Additional options to pass to the model. Default is None.
        keep_alive Optional[Union[float, str]]: The keep alive time for the model. Default is None.
        request_params Optional[Dict[str, Any]]: Additional parameters to pass to the request. Default is None.
        host Optional[str]: The host to connect to. Default is None.
        timeout Optional[Any]: The timeout for the connection. Default is None.
        client_params Optional[Dict[str, Any]]: Additional parameters to pass to the client. Default is None.
        client (OllamaClient): A pre-configured instance of the Ollama client. Default is None.
    """

    id: str = "llama3.1"
    name: str = "Ollama"
    provider: str = "Ollama"

    # Request parameters
    format: Optional[str] = None
    options: Optional[Any] = None
    keep_alive: Optional[Union[float, str]] = None
    request_params: Optional[Dict[str, Any]] = None

    # Client parameters
    host: Optional[str] = None
    timeout: Optional[Any] = None
    client_params: Optional[Dict[str, Any]] = None

    # Ollama clients
    client: Optional[OllamaClient] = None
    async_client: Optional[AsyncOllamaClient] = None

    def get_client_params(self) -> Dict[str, Any]:
        _client_params: Dict[str, Any] = {}
        if self.host is not None:
            _client_params["host"] = self.host
        if self.timeout is not None:
            _client_params["timeout"] = self.timeout
        if self.client_params is not None:
            _client_params.update(self.client_params)
        return _client_params

    def get_client(self) -> OllamaClient:
        """
        Returns an Ollama client.

        Returns:
            OllamaClient: An instance of the Ollama client.
        """
        if self.client is not None:
            return self.client

        return OllamaClient(**self.get_client_params())

    def get_async_client(self) -> AsyncOllamaClient:
        """
        Returns an asynchronous Ollama client.

        Returns:
            AsyncOllamaClient: An instance of the Ollama client.
        """
        if self.async_client is not None:
            return self.async_client

        return AsyncOllamaClient(**self.get_client_params())

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """
        Returns keyword arguments for API requests.

        Returns:
            Dict[str, Any]: The API kwargs for the model.
        """
        _request_params: Dict[str, Any] = {}
        if self.format is not None:
            _request_params["format"] = self.format
        if self.options is not None:
            _request_params["options"] = self.options
        if self.keep_alive is not None:
            _request_params["keep_alive"] = self.keep_alive
        if self.tools is not None:
            _request_params["tools"] = self.get_tools_for_api()
        if self.request_params is not None:
            _request_params.update(self.request_params)
        return _request_params

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model.
        """
        _dict = super().to_dict()
        if self.format is not None:
            _dict["format"] = self.format
        if self.options is not None:
            _dict["options"] = self.options
        if self.keep_alive is not None:
            _dict["keep_alive"] = self.keep_alive
        if self.request_params is not None:
            _dict["request_params"] = self.request_params
        return _dict

    def _format_message(self, message: Message) -> Dict[str, Any]:
        """
        Format a message into the format expected by Ollama.

        Args:
            message (Message): The message to format.

        Returns:
            Dict[str, Any]: The formatted message.
        """
        _formatted_message = {
            "role": message.role,
            "content": message.content,
        }
        if isinstance(message.model_extra, dict) and "images" in message.model_extra:
            _formatted_message["images"] = message.model_extra["images"]
        return _formatted_message

    def invoke(self, messages: List[Message]) -> Mapping[str, Any]:
        """
        Send a chat request to the Ollama API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Mapping[str, Any]: The response from the API.
        """
        return self.get_client().chat(
            model=self.id,
            messages=[self._format_message(m) for m in messages],  # type: ignore
            **self.request_kwargs,
        )  # type: ignore

    async def ainvoke(self, messages: List[Message]) -> Mapping[str, Any]:
        """
        Sends an asynchronous chat request to the Ollama API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Mapping[str, Any]: The response from the API.
        """
        return await self.get_async_client().chat(
            model=self.id,
            messages=[self._format_message(m) for m in messages],  # type: ignore
            **self.request_kwargs,
        )  # type: ignore

    def invoke_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        """
        Sends a streaming chat request to the Ollama API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Iterator[Mapping[str, Any]]: An iterator of chunks from the API.
        """
        yield from self.get_client().chat(
            model=self.id,
            messages=[self._format_message(m) for m in messages],  # type: ignore
            stream=True,
            **self.request_kwargs,
        )  # type: ignore

    async def ainvoke_stream(self, messages: List[Message]) -> Any:
        """
        Sends an asynchronous streaming chat completion request to the Ollama API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Any: An asynchronous iterator of chunks from the API.
        """
        async_stream = await self.get_async_client().chat(
            model=self.id,
            messages=[self._format_message(m) for m in messages],  # type: ignore
            stream=True,
            **self.request_kwargs,
        )
        async for chunk in async_stream:  # type: ignore
            yield chunk

    def _handle_tool_calls(
        self,
        assistant_message: Message,
        messages: List[Message],
        model_response: ModelResponse,
    ) -> Optional[ModelResponse]:
        """
        Handle tool calls in the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): The list of messages.
            model_response (ModelResponse): The model response.

        Returns:
            Optional[ModelResponse]: The model response.
        """
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            model_response.content = assistant_message.get_content_string()
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

            self._format_function_call_results(function_call_results, messages)

            return model_response
        return None

    def _update_usage_metrics(
        self,
        assistant_message: Message,
        metrics: Metrics,
        response: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """
        Update usage metrics for the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            metrics (Optional[Metrics]): The metrics for this response.
            response (Optional[Mapping[str, Any]]): The response from Ollama.
        """
        # Update time taken to generate response
        assistant_message.metrics["time"] = metrics.response_timer.elapsed
        self.metrics.setdefault("response_times", []).append(metrics.response_timer.elapsed)
        if response:
            metrics.input_tokens = response.get("prompt_eval_count", 0)
            metrics.output_tokens = response.get("eval_count", 0)
            metrics.total_tokens = metrics.input_tokens + metrics.output_tokens

            if metrics.input_tokens is not None:
                assistant_message.metrics["input_tokens"] = metrics.input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + metrics.input_tokens
            if metrics.output_tokens is not None:
                assistant_message.metrics["output_tokens"] = metrics.output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + metrics.output_tokens
            if metrics.total_tokens is not None:
                assistant_message.metrics["total_tokens"] = metrics.total_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + metrics.total_tokens
            if metrics.time_to_first_token is not None:
                assistant_message.metrics["time_to_first_token"] = metrics.time_to_first_token
                self.metrics.setdefault("time_to_first_token", []).append(metrics.time_to_first_token)

    def _get_function_calls_to_run(self, assistant_message: Message, messages: List[Message]) -> List[FunctionCall]:
        """
        Get the function calls to run from the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): The list of messages.

        Returns:
            List[FunctionCall]: The list of function calls to run.
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

    def _format_function_call_results(self, function_call_results: List[Message], messages: List[Message]) -> None:
        """
        Format the function call results and append them to the messages.

        Args:
            function_call_results (List[Message]): The list of function call results.
            messages (List[Message]): The list of messages.
        """
        if len(function_call_results) > 0:
            for _fcr in function_call_results:
                messages.append(_fcr)

    def _create_assistant_message(self, response: Mapping[str, Any], metrics: Metrics) -> Message:
        """
        Create an assistant message from the response.

        Args:
            response: The response from Ollama.
            metrics: The metrics for this response.

        Returns:
            Message: The assistant message.
        """
        message_data = MessageData()

        message_data.response_message = response.get("message")
        if message_data.response_message:
            message_data.response_content = message_data.response_message.get("content")
            message_data.response_role = message_data.response_message.get("role")
            message_data.tool_call_blocks = message_data.response_message.get("tool_calls")

        assistant_message = Message(
            role=message_data.response_role or "assistant",
            content=message_data.response_content,
        )
        if message_data.tool_call_blocks is not None:
            for block in message_data.tool_call_blocks:
                tool_call = block.get("function")
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("arguments")

                function_def = {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args) if tool_args is not None else None,
                }
                message_data.tool_calls.append({"type": "function", "function": function_def})

        if message_data.tool_calls is not None:
            assistant_message.tool_calls = message_data.tool_calls

        # Update metrics
        self._update_usage_metrics(assistant_message=assistant_message, metrics=metrics, response=response)
        return assistant_message

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Generate a response from Ollama.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            ModelResponse: The model response.
        """
        logger.debug("---------- Ollama Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()
        metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        response: Mapping[str, Any] = self.invoke(messages=messages)
        metrics.response_timer.stop()

        # -*- Create assistant message
        assistant_message = self._create_assistant_message(response=response, metrics=metrics)

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Handle tool calls
        if self._handle_tool_calls(assistant_message, messages, model_response):
            response_after_tool_calls = self.response(messages=messages)
            if response_after_tool_calls.content is not None:
                if model_response.content is None:
                    model_response.content = ""
                model_response.content += response_after_tool_calls.content
            return model_response

        # -*- Update model response
        if assistant_message.content is not None:
            model_response.content = assistant_message.get_content_string()

        logger.debug("---------- Ollama Response End ----------")
        return model_response

    async def aresponse(self, messages: List[Message]) -> ModelResponse:
        """
        Generate an asynchronous response from Ollama.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            ModelResponse: The model response.
        """
        logger.debug("---------- Ollama Async Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()
        metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        response: Mapping[str, Any] = await self.ainvoke(messages=messages)
        metrics.response_timer.stop()

        # -*- Create assistant message
        assistant_message = self._create_assistant_message(response=response, metrics=metrics)

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Handle tool calls
        if self._handle_tool_calls(assistant_message, messages, model_response):
            response_after_tool_calls = await self.aresponse(messages=messages)
            if response_after_tool_calls.content is not None:
                if model_response.content is None:
                    model_response.content = ""
                model_response.content += response_after_tool_calls.content
            return model_response

        # -*- Update model response
        if assistant_message.content is not None:
            model_response.content = assistant_message.get_content_string()

        logger.debug("---------- Ollama Async Response End ----------")
        return model_response

    def _handle_stream_tool_calls(
        self,
        assistant_message: Message,
        messages: List[Message],
    ) -> Iterator[ModelResponse]:
        """
        Handle tool calls for response stream.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): The list of messages.

        Returns:
            Iterator[ModelResponse]: An iterator of the model response.
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

            self._format_function_call_results(function_call_results, messages)

    def _handle_tool_call_chunk(self, content, tool_call_buffer, message_data) -> Tuple[str, bool]:
        """
        Handle a tool call chunk for response stream.

        Args:
            content: The content of the tool call.
            tool_call_buffer: The tool call buffer.
            message_data: The message data.

        Returns:
            Tuple[str, bool]: The tool call buffer and a boolean indicating if the tool call is complete.
        """
        tool_call_buffer += content
        brace_count = tool_call_buffer.count("{") - tool_call_buffer.count("}")

        if brace_count == 0:
            try:
                tool_call_data = json.loads(tool_call_buffer)
                message_data.tool_call_blocks.append(tool_call_data)
            except json.JSONDecodeError:
                logger.error("Failed to parse tool call JSON.")
            return "", False

        return tool_call_buffer, True

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        """
        Generate a streaming response from Ollama.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            Iterator[ModelResponse]: An iterator of the model responses.
        """
        logger.debug("---------- Ollama Response Start ----------")
        self._log_messages(messages)
        message_data = MessageData()
        ignored_content = frozenset(["json", "\n", ";", ";\n"])
        metrics: Metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        for response in self.invoke_stream(messages=messages):
            logger.debug(f"Response: {response.get('message', {}).get('content', '')}")
            message_data.response_message = response.get("message", {})
            if message_data.response_message:
                metrics.output_tokens += 1
                if metrics.output_tokens == 1:
                    metrics.time_to_first_token = metrics.response_timer.elapsed

                message_data.response_content_chunk = message_data.response_message.get("content", "").strip("`")

            if message_data.response_content_chunk:
                if message_data.in_tool_call:
                    message_data.tool_call_chunk, message_data.in_tool_call = self._handle_tool_call_chunk(
                        message_data.response_content_chunk, message_data.tool_call_chunk, message_data
                    )
                elif message_data.response_content_chunk.strip().startswith("{"):
                    message_data.in_tool_call = True
                    message_data.tool_call_chunk, message_data.in_tool_call = self._handle_tool_call_chunk(
                        message_data.response_content_chunk, message_data.tool_call_chunk, message_data
                    )
                else:
                    if message_data.response_content_chunk not in ignored_content:
                        yield ModelResponse(content=message_data.response_content_chunk)
                        message_data.response_content += message_data.response_content_chunk

            if response.get("done"):
                message_data.response_usage = response
        metrics.response_timer.stop()

        # Format tool calls
        if message_data.tool_call_blocks is not None:
            for block in message_data.tool_call_blocks:
                tool_name = block.get("name")
                tool_args = block.get("parameters")

                function_def = {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args) if tool_args is not None else None,
                }
                message_data.tool_calls.append({"type": "function", "function": function_def})

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content=message_data.response_content)

        if len(message_data.tool_calls) > 0:
            assistant_message.tool_calls = message_data.tool_calls

        # -*- Update usage metrics
        self._update_usage_metrics(
            assistant_message=assistant_message, metrics=metrics, response=message_data.response_usage
        )

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Handle tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            yield from self._handle_stream_tool_calls(assistant_message, messages)
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Ollama Response End ----------")

    async def aresponse_stream(self, messages: List[Message]) -> Any:
        """
        Generate an asynchronous streaming response from Ollama.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            Any: An asynchronous iterator of the model responses.
        """
        logger.debug("---------- Ollama Async Response Start ----------")
        self._log_messages(messages)
        message_data = MessageData()
        ignored_content = frozenset(["json", "\n", ";", ";\n"])
        metrics: Metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        async for response in self.ainvoke_stream(messages=messages):
            message_data.response_message = response.get("message", {})
            if message_data.response_message:
                metrics.output_tokens += 1
                if metrics.output_tokens == 1:
                    metrics.time_to_first_token = metrics.response_timer.elapsed

                message_data.response_content_chunk = message_data.response_message.get("content", "").strip("`")

            if message_data.response_content_chunk:
                if message_data.in_tool_call:
                    message_data.tool_call_chunk, message_data.in_tool_call = self._handle_tool_call_chunk(
                        message_data.response_content_chunk, message_data.tool_call_chunk, message_data
                    )
                elif message_data.response_content_chunk.strip().startswith("{"):
                    message_data.in_tool_call = True
                    message_data.tool_call_chunk, message_data.in_tool_call = self._handle_tool_call_chunk(
                        message_data.response_content_chunk, message_data.tool_call_chunk, message_data
                    )
                else:
                    if message_data.response_content_chunk not in ignored_content:
                        yield ModelResponse(content=message_data.response_content_chunk)
                        message_data.response_content += message_data.response_content_chunk

            if response.get("done"):
                message_data.response_usage = response
        metrics.response_timer.stop()

        # Format tool calls
        if message_data.tool_call_blocks is not None:
            for block in message_data.tool_call_blocks:
                tool_name = block.get("name")
                tool_args = block.get("parameters")

                function_def = {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args) if tool_args is not None else None,
                }
                message_data.tool_calls.append({"type": "function", "function": function_def})

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content=message_data.response_content)

        if len(message_data.tool_calls) > 0:
            assistant_message.tool_calls = message_data.tool_calls

        # -*- Update usage metrics
        self._update_usage_metrics(
            assistant_message=assistant_message, metrics=metrics, response=message_data.response_usage
        )

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Handle tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            for model_response in self._handle_stream_tool_calls(assistant_message, messages):
                yield model_response
            async for model_response in self.aresponse_stream(messages=messages):
                yield model_response
        logger.debug("---------- Ollama Async Response End ----------")
