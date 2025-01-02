from typing import Optional, List, Iterator, Dict, Any, Union

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from mistralai import Mistral, models
    from mistralai.models.chatcompletionresponse import ChatCompletionResponse
    from mistralai.models.deltamessage import DeltaMessage
    from mistralai.types.basemodel import Unset
except ImportError:
    logger.error("`mistralai` not installed")
    raise

MistralMessage = Union[models.UserMessage, models.AssistantMessage, models.SystemMessage, models.ToolMessage]


class MistralChat(LLM):
    name: str = "Mistral"
    model: str = "mistral-large-latest"
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
        if self.mistral_client:
            return self.mistral_client

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
            model=self.model,
            **self.api_kwargs,
        )
        if response is None:
            raise ValueError("Chat completion returned None")
        return response

    def invoke_stream(self, messages: List[Message]) -> Iterator[Any]:
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
            model=self.model,
            **self.api_kwargs,
        )
        if response is None:
            raise ValueError("Chat stream returned None")
        # Since response is a generator, use 'yield from' to yield its items
        yield from response

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- Mistral Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: ChatCompletionResponse = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        # logger.debug(f"Mistral response type: {type(response)}")
        # logger.debug(f"Mistral response: {response}")

        # -*- Ensure response.choices is not None
        if response.choices is None or len(response.choices) == 0:
            raise ValueError("Chat completion response has no choices")

        response_message: models.AssistantMessage = response.choices[0].message

        # -*- Create assistant message
        assistant_message = Message(
            role=response_message.role or "assistant",
            content=response_message.content,
        )
        if isinstance(response_message.tool_calls, list) and len(response_message.tool_calls) > 0:
            assistant_message.tool_calls = [t.model_dump() for t in response_message.tool_calls]

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)
        # Add token usage to metrics
        self.metrics.update(response.usage.model_dump())

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run tool calls
        logger.debug(f"Functions: {self.functions}")
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0:
            final_response = ""
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
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
                    final_response += f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    final_response += "\nRunning:"
                    for _f in function_calls_to_run:
                        final_response += f"\n - {_f.get_call_str()}"
                    final_response += "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            # -*- Get new response using result of tool call
            final_response += self.response(messages=messages)
            return final_response
        logger.debug("---------- Mistral Response End ----------")
        # -*- Return content if no function calls are present
        if assistant_message.content is not None:
            return assistant_message.get_content_string()
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Mistral Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_role = None
        assistant_message_content = ""
        assistant_message_tool_calls: Optional[List[Any]] = None
        response_timer = Timer()
        response_timer.start()
        logger.debug("Invoking stream")
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
                assistant_message_content += response_content
                yield response_content

            # -*- Parse tool calls
            if response_tool_calls is not None:
                if assistant_message_tool_calls is None:
                    assistant_message_tool_calls = []
                assistant_message_tool_calls.extend(response_tool_calls)
        logger.debug(f"Assistant message tool calls: {assistant_message_tool_calls}")
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role=(assistant_message_role or "assistant"))
        # -*- Add content to assistant message
        if assistant_message_content != "":
            assistant_message.content = assistant_message_content
        # -*- Add tool calls to assistant message
        if assistant_message_tool_calls is not None:
            assistant_message.tool_calls = [t.model_dump() for t in assistant_message_tool_calls]

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run tool calls
        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0:
            function_calls_to_run: List[FunctionCall] = []
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
                    yield f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Mistral Response End ----------")
