import json
from textwrap import dedent
from typing import Optional, List, Iterator, Dict, Any, Mapping, Union

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call, extract_tool_call_from_string

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
            messages=[self.to_llm_message(m) for m in messages],
            **self.api_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        yield from self.client.chat(
            model=self.model,
            messages=[self.to_llm_message(m) for m in messages],
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
        # Check if the response contains a tool call
        try:
            if response_content is not None:
                _response_content_clean = response_content.strip()
                if "<tool_call>" in _response_content_clean and "</tool_call>" in _response_content_clean:
                    # Extract tool call string from response
                    tool_call_content = extract_tool_call_from_string(_response_content_clean)
                    # Convert the extracted string to a dictionary
                    try:
                        logger.debug(f"Tool call content: {tool_call_content}")
                        tool_call_dict = json.loads(tool_call_content)
                    except json.JSONDecodeError:
                        raise ValueError("The content between <tool_call> tags is not a valid JSON string.")

                    tool_calls: List[Dict[str, Any]] = []
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
                    assistant_message.tool_calls = tool_calls
                    assistant_message.role = "assistant"
                # ----------------- OLD DO NOT USE -----------------
                # if _tool_call_content.startswith("{") and _tool_call_content.endswith("}"):
                #     _tool_call_content_json = json.loads(_tool_call_content)
                #     if "tool_calls" in _tool_call_content_json:
                #         assistant_tool_calls = _tool_call_content_json.get("tool_calls")
                #         if isinstance(assistant_tool_calls, list):
                #             # Build tool calls
                #             tool_calls: List[Dict[str, Any]] = []
                #             logger.debug(f"Building tool calls from {assistant_tool_calls}")
                #             for tool_call in assistant_tool_calls:
                #                 tool_call_name = tool_call.get("name")
                #                 tool_call_args = tool_call.get("arguments")
                #                 _function_def = {"name": tool_call_name}
                #                 if tool_call_args is not None:
                #                     _function_def["arguments"] = json.dumps(tool_call_args)
                #                 tool_calls.append(
                #                     {
                #                         "type": "function",
                #                         "function": _function_def,
                #                     }
                #                 )
                #             assistant_message.tool_calls = tool_calls
                #             assistant_message.role = "assistant"
        except Exception as e:
            logger.warning(f"Could not parse tool calls from: {response_content}")
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
                for _fc_message in function_call_results:
                    _fc_content = _fc_message.content
                    _fc_message.content = "<tool_response>\n" + _fc_content + "\n</tool_response>"
                    messages.append(_fc_message)
                # Reconfigure messages so the LLM is reminded of the original task
                # if self.add_user_message_after_tool_call:
                #     messages = self.add_original_user_message(messages)

            # Deactivate tool calls by turning off JSON mode after 1 tool call
            # if self.deactivate_tools_after_use:
            #     self.deactivate_function_calls()

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
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_stream(messages=messages):
            completion_tokens += 1

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
            # If the response is a tool call, it will start with a {
            if not response_is_tool_call and assistant_message_content.strip().startswith("{"):
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

        response_timer.stop()
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
                                _function_def = {"name": tool_call_name}
                                if tool_call_args is not None:
                                    _function_def["arguments"] = json.dumps(tool_call_args)
                                tool_calls.append(
                                    {
                                        "type": "function",
                                        "function": _function_def,
                                    }
                                )
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
                    yield f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run, role="user")
            # Add results of the function calls to the messages
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
                # Reconfigure messages so the LLM is reminded of the original task
                if self.add_user_message_after_tool_call:
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
                "Using the results of the tools above, respond to the following message:"
                f"\n\n<user_message>\n{original_user_message_content}\n</user_message>"
            )
            messages.append(Message(role="user", content=_content))

        return messages

    def get_instructions_to_generate_tool_calls(self) -> List[str]:
        tool_call_format = """<tool_call>{{"arguments": <args-dict>, "name": <function-name>}}</tool_call>"""
        if self.functions is not None:
            return [
                "To respond to the users message, you can use one or more of the tools provided above.",
                "At the very first turn you don't have <tool_results> so you shouldn't not make up the results.",
                "If you decide to use a tool, you must return a json object with function name and arguments within <tool_call></tool_call> XML tags as follows: "
                + "\n"
                + tool_call_format,
                "When using a tool, only respond with the tool call. Nothing else. Do not add any additional notes, explanations or white space.",
                "After you use a tool, the next message you get will contain the result of the tool call.",
                "Do not stop calling functions until the task has been accomplished or you've reached max iteration of 10.",
                "Calling multiple functions at once can overload the system and increase cost so call one function at a time please.",
                "After you use a tool and receive the result back, respond regularly to answer the users question.",
            ]
        return []

    def get_tool_call_prompt(self) -> Optional[str]:
        if self.functions is not None and len(self.functions) > 0:
            tool_call_prompt = dedent("""\
            You are a function calling AI model with self-recursion. You are provided with function signatures within <tools></tools> XML tags.
            To help with the user query, you can call one function at a time and analyse data you get from function response in the next iteration.
            Do not make assumptions about what values to plug into functions.

            Once you have called a function, results will be provided to you within <tool_response></tool_response> XML tags.
            Do not make assumptions about tool results if <tool_response> XML tags are not present since the function is not yet executed.
            Analyze the data once you get the results and call another function if needed.
            At each iteration please continue adding the your analysis to previous summary.
            Your final response should directly answer the user query.
            """)
            tool_call_prompt += "\nHere are the available tools:"
            tool_call_prompt += "\n<tools>\n"
            tool_definitions: List[str] = []
            for _f_name, _function in self.functions.items():
                _function_def = _function.get_definition_for_prompt()
                if _function_def:
                    tool_definitions.append(_function_def)
            tool_call_prompt += "\n".join(tool_definitions)
            tool_call_prompt += "\n</tools>\n\n"
            return tool_call_prompt
        return None

    def get_system_prompt_from_llm(self) -> Optional[str]:
        return self.get_tool_call_prompt()

    def get_instructions_from_llm(self) -> Optional[List[str]]:
        return self.get_instructions_to_generate_tool_calls()
