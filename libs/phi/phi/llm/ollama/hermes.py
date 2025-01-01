import json
from textwrap import dedent
from typing import Optional, List, Iterator, Dict, Any, Mapping, Union

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import (
    get_function_call_for_tool_call,
    extract_tool_call_from_string,
    remove_tool_calls_from_string,
)

try:
    from ollama import Client as OllamaClient
except ImportError:
    logger.error("`ollama` not installed")
    raise


class Hermes(LLM):
    name: str = "Hermes2Pro"
    model: str = "adrienbrault/nous-hermes2pro:Q8_0"
    host: Optional[str] = None
    timeout: Optional[Any] = None
    format: Optional[str] = None
    options: Optional[Any] = None
    keep_alive: Optional[Union[float, str]] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    ollama_client: Optional[OllamaClient] = None
    # Maximum number of function calls allowed across all iterations.
    function_call_limit: int = 5
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
        logger.debug("---------- Hermes Response Start ----------")
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
            content=response_content.strip() if response_content is not None else None,
        )
        # Check if the response contains a tool call
        try:
            if response_content is not None:
                if "<tool_call>" in response_content and "</tool_call>" in response_content:
                    # List of tool calls added to the assistant message
                    tool_calls: List[Dict[str, Any]] = []
                    # Break the response into tool calls
                    tool_call_responses = response_content.split("</tool_call>")
                    for tool_call_response in tool_call_responses:
                        # Add back the closing tag if this is not the last tool call
                        if tool_call_response != tool_call_responses[-1]:
                            tool_call_response += "</tool_call>"

                        if "<tool_call>" in tool_call_response and "</tool_call>" in tool_call_response:
                            # Extract tool call string from response
                            tool_call_content = extract_tool_call_from_string(tool_call_response)
                            # Convert the extracted string to a dictionary
                            try:
                                logger.debug(f"Tool call content: {tool_call_content}")
                                tool_call_dict = json.loads(tool_call_content)
                            except json.JSONDecodeError:
                                raise ValueError(f"Could not parse tool call from: {tool_call_content}")

                            tool_call_name = tool_call_dict.get("name")
                            tool_call_args = tool_call_dict.get("arguments")
                            function_def = {"name": tool_call_name}
                            if tool_call_args is not None:
                                function_def["arguments"] = json.dumps(tool_call_args)
                            tool_calls.append(
                                {
                                    "type": "function",
                                    "function": function_def,
                                }
                            )

                    # If tool call parsing is successful, add tool calls to the assistant message
                    if len(tool_calls) > 0:
                        assistant_message.tool_calls = tool_calls
        except Exception as e:
            logger.warning(e)
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
            # Remove the tool call from the response content
            final_response = remove_tool_calls_from_string(assistant_message.get_content_string())
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="user", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="user", tool_call_error=True, content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    final_response += f" - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    final_response += "Running:"
                    for _f in function_calls_to_run:
                        final_response += f"\n - {_f.get_call_str()}"
                    final_response += "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            if len(function_call_results) > 0:
                fc_responses = []
                for _fc_message in function_call_results:
                    fc_responses.append(
                        json.dumps({"name": _fc_message.tool_call_name, "content": _fc_message.content})
                    )

                tool_response_message_content = "<tool_response>\n" + "\n".join(fc_responses) + "\n</tool_response>"
                messages.append(Message(role="user", content=tool_response_message_content))

                for _fc_message in function_call_results:
                    _fc_message.content = (
                        "<tool_response>\n"
                        + json.dumps({"name": _fc_message.tool_call_name, "content": _fc_message.content})
                        + "\n</tool_response>"
                    )
                    messages.append(_fc_message)
                # Reconfigure messages so the LLM is reminded of the original task
                if self.add_user_message_after_tool_call:
                    messages = self.add_original_user_message(messages)

            # -*- Yield new response using results of tool calls
            final_response += self.response(messages=messages)
            return final_response
        logger.debug("---------- Hermes Response End ----------")
        # -*- Return content if no function calls are present
        if assistant_message.content is not None:
            return assistant_message.get_content_string()
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Hermes Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        tool_calls_counter = 0
        response_is_tool_call = False
        is_closing_tool_call_tag = False
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_stream(messages=messages):
            completion_tokens += 1

            # -*- Parse response
            # logger.info(f"Ollama partial response: {response}")
            # logger.info(f"Ollama partial response type: {type(response)}")
            response_message: Optional[dict] = response.get("message")
            response_content: str = response_message.get("content", "") if response_message else ""
            # logger.info(f"Ollama partial response content: {response_content}")

            # Add response content to assistant message
            if response_content is not None:
                assistant_message_content += response_content

            # Detect if response is a tool call
            # If the response is a tool call, it will start a <tool token
            if not response_is_tool_call and "<tool" in response_content:
                response_is_tool_call = True
                # logger.debug(f"Response is tool call: {response_is_tool_call}")

            # If response is a tool call, count the number of tool calls
            if response_is_tool_call:
                # If the response is an opening tool call tag, increment the tool call counter
                if "<tool" in response_content:
                    tool_calls_counter += 1

                # If the response is a closing tool call tag, decrement the tool call counter
                if assistant_message_content.strip().endswith("</tool_call>"):
                    tool_calls_counter -= 1

                # If the response is a closing tool call tag and the tool call counter is 0,
                # tool call response is complete
                if tool_calls_counter == 0 and response_content.strip().endswith(">"):
                    response_is_tool_call = False
                    # logger.debug(f"Response is tool call: {response_is_tool_call}")
                    is_closing_tool_call_tag = True

            # -*- Yield content if not a tool call and content is not None
            if not response_is_tool_call and response_content is not None:
                if is_closing_tool_call_tag and response_content.strip().endswith(">"):
                    is_closing_tool_call_tag = False
                    continue

                yield response_content

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        # Strip extra whitespaces
        assistant_message_content = assistant_message_content.strip()

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=assistant_message_content,
        )
        # Check if the response is a tool call
        try:
            if "<tool_call>" in assistant_message_content and "</tool_call>" in assistant_message_content:
                # List of tool calls added to the assistant message
                tool_calls: List[Dict[str, Any]] = []
                # Break the response into tool calls
                tool_call_responses = assistant_message_content.split("</tool_call>")
                for tool_call_response in tool_call_responses:
                    # Add back the closing tag if this is not the last tool call
                    if tool_call_response != tool_call_responses[-1]:
                        tool_call_response += "</tool_call>"

                    if "<tool_call>" in tool_call_response and "</tool_call>" in tool_call_response:
                        # Extract tool call string from response
                        tool_call_content = extract_tool_call_from_string(tool_call_response)
                        # Convert the extracted string to a dictionary
                        try:
                            logger.debug(f"Tool call content: {tool_call_content}")
                            tool_call_dict = json.loads(tool_call_content)
                        except json.JSONDecodeError:
                            raise ValueError(f"Could not parse tool call from: {tool_call_content}")

                        tool_call_name = tool_call_dict.get("name")
                        tool_call_args = tool_call_dict.get("arguments")
                        function_def = {"name": tool_call_name}
                        if tool_call_args is not None:
                            function_def["arguments"] = json.dumps(tool_call_args)
                        tool_calls.append(
                            {
                                "type": "function",
                                "function": function_def,
                            }
                        )

                # If tool call parsing is successful, add tool calls to the assistant message
                if len(tool_calls) > 0:
                    assistant_message.tool_calls = tool_calls
        except Exception:
            logger.warning(f"Could not parse tool calls from response: {assistant_message_content}")
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
                    yield f"- Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "Running:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            # Add results of the function calls to the messages
            if len(function_call_results) > 0:
                fc_responses = []
                for _fc_message in function_call_results:
                    fc_responses.append(
                        json.dumps({"name": _fc_message.tool_call_name, "content": _fc_message.content})
                    )

                tool_response_message_content = "<tool_response>\n" + "\n".join(fc_responses) + "\n</tool_response>"
                messages.append(Message(role="user", content=tool_response_message_content))
                # Reconfigure messages so the LLM is reminded of the original task
                if self.add_user_message_after_tool_call:
                    messages = self.add_original_user_message(messages)

            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Hermes Response End ----------")

    def add_original_user_message(self, messages: List[Message]) -> List[Message]:
        # Add the original user message to the messages to remind the LLM of the original task
        original_user_message_content = None
        for m in messages:
            if m.role == "user":
                original_user_message_content = m.content
                break
        if original_user_message_content is not None:
            _content = (
                "Using the tool_response above, respond to the original user message:"
                f"\n\n<user_message>\n{original_user_message_content}\n</user_message>"
            )
            messages.append(Message(role="user", content=_content))

        return messages

    def get_instructions_to_generate_tool_calls(self) -> List[str]:
        if self.functions is not None:
            return [
                "At the very first turn you don't have <tool_results> so you shouldn't not make up the results.",
                "To respond to the users message, you can use only one tool at a time.",
                "When using a tool, only respond with the tool call. Nothing else. Do not add any additional notes, explanations or white space.",
                "Do not stop calling functions until the task has been accomplished or you've reached max iteration of 10.",
            ]
        return []

    def get_tool_call_prompt(self) -> Optional[str]:
        if self.functions is not None and len(self.functions) > 0:
            tool_call_prompt = dedent(
                """\
            You are a function calling AI model with self-recursion.
            You are provided with function signatures within <tools></tools> XML tags.
            You can call only one function at a time to achieve your task.
            You may use agentic frameworks for reasoning and planning to help with user query.
            Please call a function and wait for function results to be provided to you in the next iteration.
            Don't make assumptions about what values to plug into functions.
            Once you have called a function, results will be provided to you within <tool_response></tool_response> XML tags.
            Do not make assumptions about tool results if <tool_response> XML tags are not present since the function is not yet executed.
            Analyze the results once you get them and call another function if needed.
            Your final response should directly answer the user query with an analysis or summary of the results of function calls.
            """
            )
            tool_call_prompt += "\nHere are the available tools:"
            tool_call_prompt += "\n<tools>\n"
            tool_definitions: List[str] = []
            for _f_name, _function in self.functions.items():
                _function_def = _function.get_definition_for_prompt()
                if _function_def:
                    tool_definitions.append(_function_def)
            tool_call_prompt += "\n".join(tool_definitions)
            tool_call_prompt += "\n</tools>\n\n"
            tool_call_prompt += dedent(
                """\
            Use the following pydantic model json schema for each tool call you will make: {'title': 'FunctionCall', 'type': 'object', 'properties': {'arguments': {'title': 'Arguments', 'type': 'object'}, 'name': {'title': 'Name', 'type': 'string'}}, 'required': ['arguments', 'name']}
            For each function call return a json object with function name and arguments within <tool_call></tool_call> XML tags as follows:
            <tool_call>
            {"arguments": <args-dict>, "name": <function-name>}
            </tool_call>\n
            """
            )
            return tool_call_prompt
        return None

    def get_system_prompt_from_llm(self) -> Optional[str]:
        return self.get_tool_call_prompt()

    def get_instructions_from_llm(self) -> Optional[List[str]]:
        return self.get_instructions_to_generate_tool_calls()
