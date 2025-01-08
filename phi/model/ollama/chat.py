import json
from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Mapping, Union

from pydantic import BaseModel

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from ollama import Client as OllamaClient, AsyncClient as AsyncOllamaClient
except (ModuleNotFoundError, ImportError):
    raise ImportError("`ollama` not installed. Please install using `pip install ollama`")


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

    For more information, see: https://github.com/ollama/ollama/blob/main/docs/api.md
    """

    id: str = "llama3.1"
    name: str = "Ollama"
    provider: str = "Ollama"

    # Request parameters
    format: Optional[Any] = None
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

    # Internal parameters. Not used for API requests
    # Whether to use the structured outputs with this Model.
    structured_outputs: bool = False
    # Whether the Model supports structured outputs.
    supports_structured_outputs: bool = True

    def get_client_params(self) -> Dict[str, Any]:
        client_params: Dict[str, Any] = {}
        if self.host is not None:
            client_params["host"] = self.host
        if self.timeout is not None:
            client_params["timeout"] = self.timeout
        if self.client_params is not None:
            client_params.update(self.client_params)
        return client_params

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
        request_params: Dict[str, Any] = {}
        if self.format is not None:
            request_params["format"] = self.format
        if self.options is not None:
            request_params["options"] = self.options
        if self.keep_alive is not None:
            request_params["keep_alive"] = self.keep_alive
        if self.tools is not None:
            request_params["tools"] = self.get_tools_for_api()
            # Ensure types are valid strings
            for tool in request_params["tools"]:
                for prop, obj in tool["function"]["parameters"]["properties"].items():
                    if isinstance(obj["type"], list):
                        obj["type"] = obj["type"][0]
        if self.request_params is not None:
            request_params.update(self.request_params)
        return request_params

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model.
        """
        model_dict = super().to_dict()
        if self.format is not None:
            model_dict["format"] = self.format
        if self.options is not None:
            model_dict["options"] = self.options
        if self.keep_alive is not None:
            model_dict["keep_alive"] = self.keep_alive
        if self.request_params is not None:
            model_dict["request_params"] = self.request_params
        return model_dict

    def format_message(self, message: Message) -> Dict[str, Any]:
        """
        Format a message into the format expected by Ollama.

        Args:
            message (Message): The message to format.

        Returns:
            Dict[str, Any]: The formatted message.
        """
        _message: Dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if message.role == "user":
            if message.images is not None:
                _message["images"] = message.images
        return _message

    def invoke(self, messages: List[Message]) -> Mapping[str, Any]:
        """
        Send a chat request to the Ollama API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Mapping[str, Any]: The response from the API.
        """
        request_kwargs = self.request_kwargs
        if self.response_format is not None and self.structured_outputs:
            if isinstance(self.response_format, type) and issubclass(self.response_format, BaseModel):
                logger.debug("Using structured outputs")
                format_schema = self.response_format.model_json_schema()
                if "format" not in request_kwargs:
                    request_kwargs["format"] = format_schema

        return self.get_client().chat(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            **request_kwargs,
        )  # type: ignore

    async def ainvoke(self, messages: List[Message]) -> Mapping[str, Any]:
        """
        Sends an asynchronous chat request to the Ollama API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Mapping[str, Any]: The response from the API.
        """
        request_kwargs = self.request_kwargs
        if self.response_format is not None and self.structured_outputs:
            if isinstance(self.response_format, type) and issubclass(self.response_format, BaseModel):
                logger.debug("Using structured outputs")
                format_schema = self.response_format.model_json_schema()
                if "format" not in request_kwargs:
                    request_kwargs["format"] = format_schema

        return await self.get_async_client().chat(
            model=self.id,
            messages=[self.format_message(m) for m in messages],  # type: ignore
            **request_kwargs,
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
            messages=[self.format_message(m) for m in messages],  # type: ignore
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
            messages=[self.format_message(m) for m in messages],  # type: ignore
            stream=True,
            **self.request_kwargs,
        )
        async for chunk in async_stream:  # type: ignore
            yield chunk

    def handle_tool_calls(
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
            function_calls_to_run = self.get_function_calls_to_run(assistant_message, messages)
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

            self.format_function_call_results(function_call_results, messages)

            return model_response
        return None

    def update_usage_metrics(
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

    def get_function_calls_to_run(self, assistant_message: Message, messages: List[Message]) -> List[FunctionCall]:
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

    def format_function_call_results(self, function_call_results: List[Message], messages: List[Message]) -> None:
        """
        Format the function call results and append them to the messages.

        Args:
            function_call_results (List[Message]): The list of function call results.
            messages (List[Message]): The list of messages.
        """
        if len(function_call_results) > 0:
            for _fcr in function_call_results:
                messages.append(_fcr)

    def create_assistant_message(self, response: Mapping[str, Any], metrics: Metrics) -> Message:
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
        self.update_usage_metrics(assistant_message=assistant_message, metrics=metrics, response=response)
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

        # -*- Parse structured outputs
        try:
            if (
                self.response_format is not None
                and self.structured_outputs
                and issubclass(self.response_format, BaseModel)
            ):
                parsed_object = self.response_format.model_validate_json(response.get("message", {}).get("content", ""))
                if parsed_object is not None:
                    model_response.parsed = parsed_object.model_dump_json()
        except Exception as e:
            logger.warning(f"Error parsing structured outputs: {e}")

        # -*- Create assistant message
        assistant_message = self.create_assistant_message(response=response, metrics=metrics)

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Update model response with assistant message content and audio
        if assistant_message.content is not None:
            # add the content to the model response
            model_response.content = assistant_message.get_content_string()
        if assistant_message.audio is not None:
            # add the audio to the model response
            model_response.audio = assistant_message.audio

        # -*- Handle tool calls
        if (
            self.handle_tool_calls(
                assistant_message=assistant_message, messages=messages, model_response=model_response
            )
            is not None
        ):
            return self.handle_post_tool_call_messages(messages=messages, model_response=model_response)

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

        # -*- Parse structured outputs
        try:
            if (
                self.response_format is not None
                and self.structured_outputs
                and issubclass(self.response_format, BaseModel)
            ):
                parsed_object = self.response_format.model_validate_json(response.get("message", {}).get("content", ""))
                if parsed_object is not None:
                    model_response.parsed = parsed_object.model_dump_json()
        except Exception as e:
            logger.warning(f"Error parsing structured outputs: {e}")

        # -*- Create assistant message
        assistant_message = self.create_assistant_message(response=response, metrics=metrics)

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Update model response with assistant message content and audio
        if assistant_message.content is not None:
            # add the content to the model response
            model_response.content = assistant_message.get_content_string()
        if assistant_message.audio is not None:
            # add the audio to the model response
            model_response.audio = assistant_message.audio

        # -*- Handle tool calls
        if (
            self.handle_tool_calls(
                assistant_message=assistant_message, messages=messages, model_response=model_response
            )
            is not None
        ):
            return await self.ahandle_post_tool_call_messages(messages=messages, model_response=model_response)

        logger.debug("---------- Ollama Async Response End ----------")
        return model_response

    def handle_stream_tool_calls(
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
            function_calls_to_run = self.get_function_calls_to_run(assistant_message, messages)
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

            self.format_function_call_results(function_call_results, messages)

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
        metrics: Metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        for response in self.invoke_stream(messages=messages):
            # logger.debug(f"Response: {response}")
            message_data.response_message = response.get("message", {})
            if message_data.response_message:
                metrics.output_tokens += 1
                if metrics.output_tokens == 1:
                    metrics.time_to_first_token = metrics.response_timer.elapsed

                message_data.response_content_chunk = message_data.response_message.get("content", "")
                if message_data.response_content_chunk is not None and message_data.response_content_chunk != "":
                    message_data.response_content += message_data.response_content_chunk
                    yield ModelResponse(content=message_data.response_content_chunk)

                message_data.tool_call_blocks = message_data.response_message.get("tool_calls")  # type: ignore
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

            if response.get("done"):
                message_data.response_usage = response
        metrics.response_timer.stop()

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content=message_data.response_content)

        if len(message_data.tool_calls) > 0:
            assistant_message.tool_calls = message_data.tool_calls

        # -*- Update usage metrics
        self.update_usage_metrics(
            assistant_message=assistant_message, metrics=metrics, response=message_data.response_usage
        )

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Handle tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            yield from self.handle_stream_tool_calls(assistant_message, messages)
            yield from self.handle_post_tool_call_messages_stream(messages=messages)
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
        metrics: Metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        async for response in self.ainvoke_stream(messages=messages):
            message_data.response_message = response.get("message", {})
            if message_data.response_message:
                metrics.output_tokens += 1
                if metrics.output_tokens == 1:
                    metrics.time_to_first_token = metrics.response_timer.elapsed

                message_data.response_content_chunk = message_data.response_message.get("content", "")
                if message_data.response_content_chunk is not None and message_data.response_content_chunk != "":
                    message_data.response_content += message_data.response_content_chunk
                    yield ModelResponse(content=message_data.response_content_chunk)

                message_data.tool_call_blocks = message_data.response_message.get("tool_calls")
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

            if response.get("done"):
                message_data.response_usage = response
        metrics.response_timer.stop()

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content=message_data.response_content)

        if len(message_data.tool_calls) > 0:
            assistant_message.tool_calls = message_data.tool_calls

        # -*- Update usage metrics
        self.update_usage_metrics(
            assistant_message=assistant_message, metrics=metrics, response=message_data.response_usage
        )

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Handle tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            for tool_call_response in self.handle_stream_tool_calls(assistant_message, messages):
                yield tool_call_response
            async for post_tool_call_response in self.ahandle_post_tool_call_messages_stream(messages=messages):
                yield post_tool_call_response
        logger.debug("---------- Ollama Async Response End ----------")

    def model_copy(self, *, update: Optional[Mapping[str, Any]] = None, deep: bool = False) -> "Ollama":
        new_model = Ollama(**self.model_dump(exclude={"client"}), client=self.client)
        return new_model
