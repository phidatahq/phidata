import json
from textwrap import dedent
from typing import Optional, List, Iterator, Dict, Any, Mapping, Union

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.llm.ollama.utils import extract_tool_calls
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
    model: str = "openhermes"
    host: Optional[str] = None
    timeout: Optional[Any] = None
    format: Optional[str] = None
    options: Optional[Any] = None
    keep_alive: Optional[Union[float, str]] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    ollama_client: Optional[OllamaClient] = None
    # Maximum number of function calls allowed across all iterations.
    function_call_limit: int = 10
    # Deactivate tool calls after 1 tool call
    deactivate_tools_after_use: bool = False
    # After a tool call is run, add the user message as a reminder to the LLM
    add_user_message_after_tool_call: bool = True

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
        # elif self.functions is not None:
        #     kwargs["format"] = "json"
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

    def invoke(self, messages: List[Message]) -> Mapping[str, Any]:
        return self.client.chat(
            model=self.model,
            messages=[self.to_llm_message(m) for m in messages],  # type: ignore
            **self.api_kwargs,
        )  # type: ignore

    def invoke_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        yield from self.client.chat(
            model=self.model,
            messages=[self.to_llm_message(m) for m in messages],  # type: ignore
            stream=True,
            **self.api_kwargs,
        )  # type: ignore

    def deactivate_function_calls(self) -> None:
        # Deactivate tool calls by turning off JSON mode after 1 tool call
        # This is triggered when the function call limit is reached.
        self.format = ""

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- Ollama Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: Mapping[str, Any] = self.invoke(messages=messages)
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
                assistant_tool_calls = extract_tool_calls(_tool_call_content)

                if assistant_tool_calls.invalid_json_format:
                    assistant_message.tool_call_error = True

                if assistant_tool_calls.tool_calls is not None:
                    # Build tool calls
                    tool_calls: List[Dict[str, Any]] = []
                    logger.debug(f"Building tool calls from {assistant_tool_calls}")
                    for tool_call in assistant_tool_calls.tool_calls:
                        tool_call_name = tool_call.get("name")
                        tool_call_args = tool_call.get("arguments")
                        _function_def = {"name": tool_call_name}
                        if tool_call_args is not None:
                            _function_def["arguments"] = json.dumps(tool_call_args)
                        tool_calls.append(
                            {
                                "type": "function",
                                "function": _function_def,
                            }
                        )

                    # Add tool calls to assistant message
                    assistant_message.tool_calls = tool_calls
                    assistant_message.role = "assistant"
        except Exception:
            logger.warning(f"Could not parse tool calls from response: {response_content}")
            assistant_message.tool_call_error = True
            pass

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        # Currently there is a bug in Ollama where sometimes the input tokens are not always returned
        input_tokens = response.get("prompt_eval_count", 0)
        output_tokens = response.get("eval_count", 0)

        assistant_message.metrics["input_tokens"] = input_tokens
        assistant_message.metrics["output_tokens"] = output_tokens

        self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + input_tokens
        self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + output_tokens
        self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + input_tokens + output_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function call
        final_response = ""
        if assistant_message.tool_call_error:
            # Add error message to the messages to let the LLM know that the tool call failed
            messages = self.add_tool_call_error_message(messages)

            # -*- Yield new response using results of tool calls
            final_response += self.response(messages=messages)
            return final_response

        elif assistant_message.tool_calls is not None and self.run_tools:
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
                    final_response += "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")

            # This case rarely happens but it should be handled
            if len(function_calls_to_run) != len(function_call_results):
                return final_response + self.response(messages=messages)

            # Add results of the function calls to the messages
            elif len(function_call_results) > 0:
                messages.extend(function_call_results)
                # Reconfigure messages so the LLM is reminded of the original task
                if self.add_user_message_after_tool_call:
                    if any(item.tool_call_error for item in function_call_results):
                        messages = self.add_tool_call_error_message(messages)
                    else:
                        messages = self.add_original_user_message(messages)

            # Deactivate tool calls by turning off JSON mode after 1 tool call
            if self.deactivate_tools_after_use:
                self.deactivate_function_calls()

            # -*- Yield new response using results of tool calls
            final_response += self.response(messages=messages)
            return final_response

        logger.debug("---------- Ollama Response End ----------")

        # -*- Return content if no function calls are present
        if assistant_message.content is not None:
            return assistant_message.get_content_string()

        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Ollama Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        response_is_tool_call = False
        tool_call_bracket_count = 0
        is_last_tool_call_bracket = False
        completion_tokens = 0
        time_to_first_token = None
        response_metrics: Mapping[str, Any] = {}
        response_timer = Timer()
        response_timer.start()

        for response in self.invoke_stream(messages=messages):
            completion_tokens += 1
            if completion_tokens == 1:
                time_to_first_token = response_timer.elapsed
                logger.debug(f"Time to first token: {time_to_first_token:.4f}s")

            # -*- Parse response
            # logger.info(f"Ollama partial response: {response}")
            # logger.info(f"Ollama partial response type: {type(response)}")
            response_message: Optional[dict] = response.get("message")
            response_content = response_message.get("content") if response_message else None
            # logger.info(f"Ollama partial response content: {response_content}")

            # Add response content to assistant message
            if response_content is not None:
                assistant_message_content += response_content

            # Strip out tool calls from the response
            extract_tool_calls_result = extract_tool_calls(assistant_message_content)
            if not response_is_tool_call and (
                extract_tool_calls_result.tool_calls is not None or extract_tool_calls_result.invalid_json_format
            ):
                response_is_tool_call = True

            # If the response is a tool call, count the number of brackets
            if response_is_tool_call and response_content is not None:
                if "{" in response_content.strip():
                    # Add the number of opening brackets to the count
                    tool_call_bracket_count += response_content.strip().count("{")
                    # logger.debug(f"Tool call bracket count: {tool_call_bracket_count}")
                if "}" in response_content.strip():
                    # Subtract the number of closing brackets from the count
                    tool_call_bracket_count -= response_content.strip().count("}")
                    # Check if the response is the last bracket
                    if tool_call_bracket_count == 0:
                        response_is_tool_call = False
                        is_last_tool_call_bracket = True
                    # logger.debug(f"Tool call bracket count: {tool_call_bracket_count}")

            # -*- Yield content if not a tool call and content is not None
            if not response_is_tool_call and response_content is not None:
                if is_last_tool_call_bracket and response_content.strip().endswith("}"):
                    is_last_tool_call_bracket = False
                    continue

                yield response_content

            if response.get("done"):
                response_metrics = response

        response_timer.stop()
        logger.debug(f"Tokens generated: {completion_tokens}")
        if completion_tokens > 0:
            logger.debug(f"Time per output token: {response_timer.elapsed / completion_tokens:.4f}s")
            logger.debug(f"Throughput: {completion_tokens / response_timer.elapsed:.4f} tokens/s")
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=assistant_message_content,
        )

        # Check if the response is a tool call
        try:
            if response_is_tool_call and assistant_message_content != "":
                _tool_call_content = assistant_message_content.strip()
                assistant_tool_calls = extract_tool_calls(_tool_call_content)

                if assistant_tool_calls.invalid_json_format:
                    assistant_message.tool_call_error = True

                if not assistant_message.tool_call_error and assistant_tool_calls.tool_calls is not None:
                    # Build tool calls
                    tool_calls: List[Dict[str, Any]] = []
                    logger.debug(f"Building tool calls from {assistant_tool_calls.tool_calls}")
                    for tool_call in assistant_tool_calls.tool_calls:
                        tool_call_name = tool_call.get("name")
                        tool_call_args = tool_call.get("arguments")
                        _function_def = {"name": tool_call_name}
                        if tool_call_args is not None:
                            _function_def["arguments"] = json.dumps(tool_call_args)
                        tool_calls.append(
                            {
                                "type": "function",
                                "function": _function_def,
                            }
                        )

                    # Add tool calls to assistant message
                    assistant_message.tool_calls = tool_calls
        except Exception:
            logger.warning(f"Could not parse tool calls from response: {assistant_message_content}")
            assistant_message.tool_call_error = True
            pass

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = f"{response_timer.elapsed:.4f}"
        if time_to_first_token is not None:
            assistant_message.metrics["time_to_first_token"] = f"{time_to_first_token:.4f}s"
        if completion_tokens > 0:
            assistant_message.metrics["time_per_output_token"] = f"{response_timer.elapsed / completion_tokens:.4f}s"
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)
        if time_to_first_token is not None:
            if "time_to_first_token" not in self.metrics:
                self.metrics["time_to_first_token"] = []
            self.metrics["time_to_first_token"].append(f"{time_to_first_token:.4f}s")
        if completion_tokens > 0:
            if "tokens_per_second" not in self.metrics:
                self.metrics["tokens_per_second"] = []
            self.metrics["tokens_per_second"].append(f"{completion_tokens / response_timer.elapsed:.4f}")

        # Add token usage to metrics
        # Currently there is a bug in Ollama where sometimes the input tokens are not returned
        input_tokens = response_metrics.get("prompt_eval_count", 0)
        output_tokens = response_metrics.get("eval_count", 0)

        assistant_message.metrics["input_tokens"] = input_tokens
        assistant_message.metrics["output_tokens"] = output_tokens

        self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + input_tokens
        self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + output_tokens
        self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + input_tokens + output_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function call
        if assistant_message.tool_call_error:
            # Add error message to the messages to let the LLM know that the tool call failed
            messages = self.add_tool_call_error_message(messages)

            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)

        elif assistant_message.tool_calls is not None and self.run_tools:
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
                    yield f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")

            # This case rarely happens but it should be handled
            if len(function_calls_to_run) != len(function_call_results):
                messages = self.add_tool_call_error_message(messages)

            # Add results of the function calls to the messages
            elif len(function_call_results) > 0:
                messages.extend(function_call_results)

                # Reconfigure messages so the LLM is reminded of the original task
                if self.add_user_message_after_tool_call:
                    if any(item.tool_call_error for item in function_call_results):
                        messages = self.add_tool_call_error_message(messages)
                    else:
                        messages = self.add_original_user_message(messages)

            # Deactivate tool calls by turning off JSON mode after 1 tool call
            if self.deactivate_tools_after_use:
                self.deactivate_function_calls()

            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)

        logger.debug("---------- Ollama Response End ----------")

    def add_original_user_message(self, messages: List[Message]) -> List[Message]:
        # Add the original user message to the messages to remind the LLM of the original task
        original_user_message_content = None
        for m in messages:
            if m.role == "user":
                original_user_message_content = m.content
                break

        if original_user_message_content is not None:
            _content = (
                "Using the results of the tools above, respond to the following message. "
                "If the user explicitly requests raw data or specific formats like JSON, provide it as requested. "
                "Otherwise, use the tool results to provide a clear and relevant answer without "
                "returning the raw results directly:"
                f"\n\n<user_message>\n{original_user_message_content}\n</user_message>"
            )

            messages.append(Message(role="user", content=_content))

        return messages

    def add_tool_call_error_message(self, messages: List[Message]) -> List[Message]:
        # Add error message to the messages to let the LLM know that the tool call failed
        content = (
            "Output from the tool indicates an arguments error, take a step back and adjust the tool arguments "
            "then use the same tool again with the new arguments. "
            "Ensure the response does not mention any failed tool calls, Just the adjusted tool calls."
        )
        messages.append(Message(role="user", tool_call_error=True, content=content))
        return messages

    def get_instructions_to_generate_tool_calls(self) -> List[str]:
        if self.functions is not None:
            return [
                "To respond to the users message, you can use one or more of the tools provided above.",
                # Tool usage instructions
                "If you decide to use a tool, you must respond in the JSON format matching the following schema:\n"
                + dedent(
                    """\
                    {
                        "tool_calls": [
                            {
                                "name": "<name of the selected tool>",
                                "arguments": <parameters for the selected tool, matching the tool's JSON schema>
                            }
                        ]
                    }\
                    """
                ),
                "REMEMBER: To use a tool, you MUST respond ONLY in JSON format.",
                (
                    "REMEMBER: You can use multiple tools in a single response if necessary, "
                    'by including multiple entries in the "tool_calls" array.'
                ),
                "You may use the same tool multiple times in a single response, but only with different arguments.",
                (
                    "To use a tool, ONLY respond with the JSON matching the schema. Nothing else. "
                    "Do not add any additional notes or explanations"
                ),
                (
                    "REMEMBER: The ONLY valid way to use this tool is to ensure the ENTIRE response is in JSON format, "
                    "matching the specified schema."
                ),
                "Do not inform the user that you used a tool in your response.",
                "Do not suggest tools to use in your responses. You should use them to obtain answers.",
                "Ensure each tool use is formatted correctly and independently.",
                'REMEMBER: The "arguments" field must contain valid parameters as per the tool\'s JSON schema.',
                "Ensure accuracy by using tools to obtain your answers, avoiding assumptions about tool output.",
                # Response instructions
                "After you use a tool, the next message you get will contain the result of the tool use.",
                "If the result of one tool requires using another tool, use needed tool first and then use the result.",
                (
                    "If the result from a tool indicates an input error, "
                    "You must adjust the parameters and try use the tool again."
                ),
                (
                    "If the tool results are used in your response, you do not need to mention the knowledge cutoff. "
                    "Use the information directly from the tool's output, which is assumed to be up-to-date."
                ),
                (
                    "After you use a tool and receive the result back, take a step back and provide clear and relevant "
                    "answers based on the user's query and tool results."
                ),
            ]
        return []

    def get_tool_calls_definition(self) -> Optional[str]:
        if self.functions is not None:
            _tool_choice_prompt = "To respond to the users message, you have access to the following tools:"
            for _f_name, _function in self.functions.items():
                _function_definition = _function.get_definition_for_prompt()
                if _function_definition:
                    _tool_choice_prompt += f"\n{_function_definition}"
            _tool_choice_prompt += "\n\n"
            return _tool_choice_prompt
        return None

    def get_system_prompt_from_llm(self) -> Optional[str]:
        return self.get_tool_calls_definition()

    def get_instructions_from_llm(self) -> Optional[List[str]]:
        return self.get_instructions_to_generate_tool_calls()
