import json

from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Mapping, Tuple

from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.model.ollama.chat import Ollama, Metrics
from phi.utils.log import logger


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
    end_tool_call: bool = False
    response_usage: Optional[Mapping[str, Any]] = None


class Hermes(Ollama):
    """
    A class for interacting with the Hermes model via Ollama. This is a subclass of the Ollama model,
    which customizes tool call streaming for the hermes3 model.

    Attributes:
        id (str): The ID of the model.
        name (str): The name of the model.
        provider (Optional[str]): The provider of the model.
    """

    id: str = "hermes3"
    name: str = "Hermes"
    provider: str = "Ollama"

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
        if content != "</tool_call>":
            tool_call_buffer += content

        if message_data.end_tool_call:
            try:
                tool_call_data = json.loads(tool_call_buffer)
                message_data.tool_call_blocks.append(tool_call_data)
                message_data.end_tool_call = False
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
        logger.debug("---------- Ollama Hermes Response Start ----------")
        self._log_messages(messages)
        message_data = MessageData()
        metrics: Metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        for response in self.invoke_stream(messages=messages):
            message_data.response_message = response.get("message", {})
            if message_data.response_message:
                metrics.output_tokens += 1
                if metrics.output_tokens == 1:
                    metrics.time_to_first_token = metrics.response_timer.elapsed

                message_data.response_content_chunk = message_data.response_message.get("content", "").strip("`")

            if message_data.response_content_chunk:
                if message_data.response_content_chunk.strip().startswith("</tool_call>"):
                    message_data.end_tool_call = True
                if message_data.in_tool_call:
                    message_data.tool_call_chunk, message_data.in_tool_call = self._handle_tool_call_chunk(
                        message_data.response_content_chunk, message_data.tool_call_chunk, message_data
                    )
                elif message_data.response_content_chunk.strip().startswith("<tool_call>"):
                    message_data.in_tool_call = True
                else:
                    yield ModelResponse(content=message_data.response_content_chunk)
                    message_data.response_content += message_data.response_content_chunk

            if response.get("done"):
                message_data.response_usage = response
        metrics.response_timer.stop()

        # Format tool calls
        if message_data.tool_call_blocks is not None:
            for block in message_data.tool_call_blocks:
                tool_name = block.get("name")
                tool_args = block.get("arguments")

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
        logger.debug("---------- Ollama Hermes Response End ----------")

    async def aresponse_stream(self, messages: List[Message]) -> Any:
        """
        Generate an asynchronous streaming response from Ollama.

        Args:
            messages (List[Message]): A list of messages.

        Returns:
            Any: An asynchronous iterator of the model responses.
        """
        logger.debug("---------- Ollama Hermes Async Response Start ----------")
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

                message_data.response_content_chunk = message_data.response_message.get("content", "").strip("`")

            if message_data.response_content_chunk:
                if message_data.response_content_chunk.strip().startswith("</tool_call>"):
                    message_data.end_tool_call = True
                if message_data.in_tool_call:
                    message_data.tool_call_chunk, message_data.in_tool_call = self._handle_tool_call_chunk(
                        message_data.response_content_chunk, message_data.tool_call_chunk, message_data
                    )
                elif message_data.response_content_chunk.strip().startswith("<tool_call>"):
                    message_data.in_tool_call = True
                else:
                    yield ModelResponse(content=message_data.response_content_chunk)
                    message_data.response_content += message_data.response_content_chunk

            if response.get("done"):
                message_data.response_usage = response
        metrics.response_timer.stop()

        # Format tool calls
        if message_data.tool_call_blocks is not None:
            for block in message_data.tool_call_blocks:
                tool_name = block.get("name")
                tool_args = block.get("arguments")

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
        logger.debug("---------- Ollama Hermes Async Response End ----------")
