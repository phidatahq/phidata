import json
from typing import Optional, List, Iterator, Dict, Any, Mapping, Union

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from ollama import Client as OllamaClient
except ImportError:
    logger.error("`ollama` not installed")
    raise


class Ollama(LLM):
    name: str = "Ollama"
    model: str = "llama2"
    host: Optional[str] = None
    timeout: Optional[Any] = None
    format: Optional[str] = None
    options: Optional[Any] = None
    keep_alive: Optional[Union[float, str]] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    ollama_client: Optional[OllamaClient] = None
    generate_tool_calls_from_json_mode: bool = False

    @property
    def client(self) -> OllamaClient:
        if self.ollama_client:
            return self.ollama_client

        _ollama_params: Dict[str, Any] = {}
        if self.host:
            _ollama_params["host"] = self.host
        if self.timeout:
            _ollama_params["timeout"] = self.timeout
        if self.client_kwargs:
            _ollama_params.update(self.client_kwargs)
        return OllamaClient(**_ollama_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.format is not None:
            kwargs["format"] = self.format
        elif self.response_format is not None:
            if self.response_format.get("type") == "json_object":
                kwargs["format"] = "json"
        elif self.generate_tool_calls_from_json_mode:
            kwargs["format"] = "json"
        if self.options is not None:
            kwargs["options"] = self.options
        if self.keep_alive is not None:
            kwargs["keep_alive"] = self.keep_alive
        return kwargs

    def to_dict(self) -> Dict[str, Any]:
        _dict = super().to_dict()
        if self.host:
            _dict["host"] = self.host
        if self.timeout:
            _dict["timeout"] = self.timeout
        if self.format:
            _dict["format"] = self.format
        if self.response_format:
            _dict["response_format"] = self.response_format
        return _dict

    def to_llm_message(self, message: Message) -> Dict[str, Any]:
        msg = {
            "role": message.role,
            "content": message.content,
        }
        if message.model_extra is not None and "images" in message.model_extra:
            msg["images"] = message.model_extra.get("images")
        return msg

    def invoke_model(self, messages: List[Message]) -> Mapping[str, Any]:
        return self.client.chat(
            model=self.model,
            messages=[self.to_llm_message(m) for m in messages],
            **self.api_kwargs,
        )

    def invoke_model_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        yield from self.client.chat(
            model=self.model,
            messages=[self.to_llm_message(m) for m in messages],
            stream=True,
            **self.api_kwargs,
        )  # type: ignore

    def parsed_response(self, messages: List[Message]) -> str:
        logger.debug("---------- Ollama Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: Mapping[str, Any] = self.invoke_model(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        # logger.debug(f"Ollama response type: {type(response)}")
        # logger.debug(f"Ollama response: {response}")

        # -*- Parse response
        response_message: Mapping[str, Any] = response.get("message")  # type: ignore
        response_role = response_message.get("role")
        response_content: Optional[str] = response_message.get("content")

        # -*- Create assistant message
        assistant_message = Message(
            role=response_role or "assistant",
            content=response_content,
        )
        # Check if the response is a tool call
        try:
            if response_content is not None:
                _tool_call_content = response_content.strip()
                if _tool_call_content.startswith("{") and _tool_call_content.endswith("}"):
                    _tool_call_content_json = json.loads(_tool_call_content)
                    if "tool_calls" in _tool_call_content_json:
                        assistant_tool_calls = _tool_call_content_json.get("tool_calls")
                        if isinstance(assistant_tool_calls, list):
                            # Build tool calls
                            tool_calls: List[Dict[str, Any]] = []
                            logger.debug(f"Building tool calls from {assistant_tool_calls}")
                            for tool_call in assistant_tool_calls:
                                tool_call_name = tool_call.get("name")
                                tool_call_args = tool_call.get("arguments")
                                _function_def = {
                                    "name": tool_call_name,
                                    "arguments": json.dumps(tool_call_args),
                                }
                                tool_calls.append(
                                    {
                                        "type": "function",
                                        "function": _function_def,
                                    }
                                )
                            assistant_message.tool_calls = tool_calls
                            assistant_message.role = "assistant"
        except Exception:
            pass

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function call
        if assistant_message.tool_calls is not None and self.run_tools:
            final_response = ""
            function_calls_to_run: List[FunctionCall] = []
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
                    final_response += f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    final_response += "\nRunning:"
                    for _f in function_calls_to_run:
                        final_response += f"\n - {_f.get_call_str()}"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            self.format = ""
            # -*- Yield new response using results of tool calls
            final_response += self.parsed_response(messages=messages)
            return final_response
        logger.debug("---------- Ollama Response End ----------")
        # -*- Return content if no function calls are present
        if assistant_message.content is not None:
            return assistant_message.get_content_string()
        return "Something went wrong, please try again."

    def parsed_response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Ollama Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        response_content: Optional[str] = None
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_model_stream(messages=messages):
            completion_tokens += 1

            # -*- Parse response
            # logger.info(f"Ollama partial response: {response}")
            # logger.info(f"Ollama partial response type: {type(response)}")
            response_message: Optional[dict] = response.get("message")
            response_content = response_message.get("content") if response_message else None
            # logger.info(f"Ollama partial response content: {response_content}")

            # -*- Return content if present
            if response_content is not None:
                assistant_message_content += response_content
                yield response_content

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=assistant_message_content,
        )
        # Check if the response is a tool call
        try:
            if response_content is not None:
                _tool_call_content = assistant_message_content.strip()
                if _tool_call_content.startswith("{") and _tool_call_content.endswith("}"):
                    _tool_call_content_json = json.loads(_tool_call_content)
                    if "tool_calls" in _tool_call_content_json:
                        assistant_tool_calls = _tool_call_content_json.get("tool_calls")
                        if isinstance(assistant_tool_calls, list):
                            # Build tool calls
                            tool_calls: List[Dict[str, Any]] = []
                            logger.debug(f"Building tool calls from {assistant_tool_calls}")
                            for tool_call in assistant_tool_calls:
                                tool_call_name = tool_call.get("name")
                                tool_call_args = tool_call.get("arguments")
                                _function_def = {
                                    "name": tool_call_name,
                                    "arguments": json.dumps(tool_call_args),
                                }
                                tool_calls.append(
                                    {
                                        "type": "function",
                                        "function": _function_def,
                                    }
                                )
                            assistant_message.tool_calls = tool_calls
                            assistant_message.role = "assistant"
        except Exception:
            pass

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function call
        if assistant_message.tool_calls is not None and self.run_tools:
            function_calls_to_run: List[FunctionCall] = []
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
                    yield f"\n\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\n\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            self.format = ""
            self.generate_tool_calls_from_json_mode = False
            # -*- Yield new response using results of tool calls
            yield from self.parsed_response_stream(messages=messages)
        logger.debug("---------- Ollama Response End ----------")
