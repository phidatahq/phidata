import json
from typing import Optional, List, Iterator, Dict, Any, Union, cast

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
    name: str = "claude"
    model: str = "claude-3-5-sonnet-2024062"
    # -*- Request parameters
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    request_params: Optional[Dict[str, Any]] = None
    # -*- Client parameters
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    # -*- Provide the client manually
    anthropic_client: Optional[AnthropicClient] = None

    @property
    def client(self) -> AnthropicClient:
        if self.anthropic_client:
            return self.anthropic_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        return AnthropicClient(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        _request_params: Dict[str, Any] = {}
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.stop_sequences:
            _request_params["stop_sequences"] = self.stop_sequences
        if self.tools is not None:
            if _request_params.get("stop_sequences") is None:
                _request_params["stop_sequences"] = ["</function_calls>"]
            elif "</function_calls>" not in _request_params["stop_sequences"]:
                _request_params["stop_sequences"].append("</function_calls>")
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.top_k:
            _request_params["top_k"] = self.top_k
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def get_tools(self):
        """
        Refactors the tools in a format accepted by the Anthropic API.
        """
        if not self.functions:
            return None

        tools: List = []
        for f_name, function in self.functions.items():
            required_params = [
                param_name
                for param_name, param_info in function.parameters.get("properties", {}).items()
                if "null"
                not in (
                    param_info.get("type") if isinstance(param_info.get("type"), list) else [param_info.get("type")]
                )
            ]
            tools.append(
                {
                    "name": f_name,
                    "description": function.description or "",
                    "input_schema": {
                        "type": function.parameters.get("type") or "object",
                        "properties": {
                            param_name: {
                                "type": param_info.get("type") or "",
                                "description": param_info.get("description") or "",
                            }
                            for param_name, param_info in function.parameters.get("properties", {}).items()
                        },
                        "required": required_params,
                    },
                }
            )
        return tools

    def invoke(self, messages: List[Message]) -> AnthropicMessage:
        api_kwargs: Dict[str, Any] = self.api_kwargs
        api_messages: List[dict] = []
        system_messages: List[str] = []

        for idx, message in enumerate(messages):
            if message.role == "system" or (message.role != "user" and idx in [0, 1]):
                system_messages.append(message.content)  # type: ignore
            else:
                api_messages.append({"role": message.role, "content": message.content or ""})

        api_kwargs["system"] = " ".join(system_messages)

        if self.tools:
            api_kwargs["tools"] = self.get_tools()

        return self.client.messages.create(
            model=self.model,
            messages=api_messages,  # type: ignore
            **api_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Any:
        api_kwargs: Dict[str, Any] = self.api_kwargs
        api_messages: List[dict] = []
        system_messages: List[str] = []

        for idx, message in enumerate(messages):
            if message.role == "system" or (message.role != "user" and idx in [0, 1]):
                system_messages.append(message.content)  # type: ignore
            else:
                api_messages.append({"role": message.role, "content": message.content or ""})

        api_kwargs["system"] = " ".join(system_messages)

        if self.tools:
            api_kwargs["tools"] = self.get_tools()

        return self.client.messages.stream(
            model=self.model,
            messages=api_messages,  # type: ignore
            **api_kwargs,
        )

    def response(self, messages: List[Message]) -> ModelResponse:
        logger.debug("---------- Claude Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        # -*- Create a ModelResponse object to return
        model_response = ModelResponse()

        response_timer = Timer()
        response_timer.start()
        response: AnthropicMessage = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # logger.debug(f"Response: {response}")
        # logger.debug(f"Response content: {response.content[0]}")

        # -*- Parse response
        response_content: str = ""
        response_block: Union[TextBlock, ToolUseBlock] = response.content[0]
        if isinstance(response_block, TextBlock):
            response_content = response_block.text
        elif isinstance(response_block, ToolUseBlock):
            tool_block = cast(dict[str, Any], response_block.input)
            response_content = tool_block.get("query", "")

        # -*- Create agent message
        agent_message = Message(
            role=response.role or "assistant",
            content=response_content,
        )

        # Check if the response contains a tool call
        if response.stop_reason == "tool_use":
            tool_calls: List[Dict[str, Any]] = []
            tool_ids: List[str] = []
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
            agent_message.content = response.content

            if len(tool_calls) > 0:
                agent_message.tool_calls = tool_calls

        # -*- Update usage metrics
        # Add response time to metrics
        agent_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        response_usage: Usage = response.usage
        if response_usage:
            input_tokens = response_usage.input_tokens
            output_tokens = response_usage.output_tokens

            if input_tokens is not None:
                agent_message.metrics["input_tokens"] = input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + input_tokens

            if output_tokens is not None:
                agent_message.metrics["output_tokens"] = output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + output_tokens

            if input_tokens is not None and output_tokens is not None:
                agent_message.metrics["total_tokens"] = input_tokens + output_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + input_tokens + output_tokens

        # -*- Add agent message to messages
        messages.append(agent_message)
        agent_message.log()

        # -*- Parse and run function call
        if agent_message.tool_calls is not None and self.run_tools:
            # Remove the tool call from the response content
            model_response.content = str(response_content)
            model_response.content += "\n\n"
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in agent_message.tool_calls:
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

            function_call_results = self.run_function_calls(function_calls_to_run)
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

            # -*- Yield new response using results of tool calls
            response_after_tool_calls = self.response(messages=messages)
            if response_after_tool_calls.content is not None:
                model_response.content += response_after_tool_calls.content
            return model_response
        # -*- Return content if no function calls are present
        if agent_message.content is not None:
            model_response.content = agent_message.get_content_string()

        logger.debug("---------- Claude Response End ----------")
        return model_response

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        logger.debug("---------- Claude Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_content_text = ""
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

        # -*- Create agent message
        agent_message = Message(
            role="assistant",
            content="",
        )
        agent_message.content = response_content

        if len(tool_calls) > 0:
            agent_message.tool_calls = tool_calls

        # -*- Update usage metrics
        # Add response time to metrics
        agent_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        if response_usage:
            input_tokens = response_usage.input_tokens
            output_tokens = response_usage.output_tokens

            if input_tokens is not None:
                agent_message.metrics["input_tokens"] = input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + input_tokens

            if output_tokens is not None:
                agent_message.metrics["output_tokens"] = output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + output_tokens

            if input_tokens is not None and output_tokens is not None:
                agent_message.metrics["total_tokens"] = input_tokens + output_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + input_tokens + output_tokens

        # -*- Add agent message to messages
        messages.append(agent_message)
        agent_message.log()

        # -*- Parse and run function call
        if agent_message.tool_calls is not None and self.run_tools:
            # Remove the tool call from the response content
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in agent_message.tool_calls:
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

            function_call_results = self.run_function_calls(function_calls_to_run)
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

            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Claude Response End ----------")

    def get_tool_call_prompt(self) -> Optional[str]:
        if self.functions is not None and len(self.functions) > 0:
            tool_call_prompt = "Do not reflect on the quality of the returned search results in your response"
            return tool_call_prompt
        return None

    def get_system_prompt_from_model(self) -> Optional[str]:
        return self.get_tool_call_prompt()
