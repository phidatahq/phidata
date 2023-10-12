import json
from typing import Optional, List, Iterator, Dict, Any

from phi.llm.base import LLM
from phi.llm.schemas import Message, FunctionCall
from phi.utils.env import get_from_env
from phi.utils.log import logger
from phi.utils.timer import Timer

try:
    import openai  # noqa: F401
    from openai.openai_object import OpenAIObject  # noqa: F401
except ImportError:
    logger.error("`openai` not installed")
    raise


class OpenAIChat(LLM):
    name: str = "OpenAIChat"
    model: str = "gpt-3.5-turbo-16k"
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    user: Optional[str] = None
    top_p: Optional[float] = None
    logit_bias: Optional[Any] = None
    headers: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        _dict = super().to_dict()
        _dict["max_tokens"] = self.max_tokens
        _dict["temperature"] = self.temperature
        return _dict

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens
        if self.temperature:
            kwargs["temperature"] = self.temperature
        if self.functions:
            kwargs["functions"] = [f.to_dict() for f in self.functions.values()]
            if self.function_call is not None:
                kwargs["function_call"] = self.function_call
        if self.frequency_penalty:
            kwargs["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty:
            kwargs["presence_penalty"] = self.presence_penalty
        if self.stop:
            kwargs["stop"] = self.stop
        if self.user:
            kwargs["user"] = self.user
        if self.top_p:
            kwargs["top_p"] = self.top_p
        if self.logit_bias:
            kwargs["logit_bias"] = self.logit_bias
        if self.headers:
            kwargs["headers"] = self.headers
        return kwargs

    def invoke_model(self, messages: List[Message]) -> OpenAIObject:
        if get_from_env("OPENAI_API_KEY") is None:
            logger.debug("--o-o-- Using Phidata Servers")
            try:
                from phi.api.llm import openai_chat

                response_dict = openai_chat(
                    params={
                        "model": self.model,
                        "messages": [m.to_dict() for m in messages],
                        **self.api_kwargs,
                    }
                )
                if response_dict is None:
                    logger.error("Error: Could not reach Phidata Servers.")
                    logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                return OpenAIObject.construct_from(response_dict)
            except Exception as e:
                logger.exception(e)
                logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                exit(1)
        else:
            return openai.ChatCompletion.create(
                model=self.model,
                messages=[m.to_dict() for m in messages],
                **self.api_kwargs,
            )

    def invoke_model_stream(self, messages: List[Message]) -> Iterator[OpenAIObject]:
        if get_from_env("OPENAI_API_KEY") is None:
            logger.debug("--o-o-- Using Phidata Servers")
            try:
                from phi.api.llm import openai_chat_stream
                from openai import util as openai_util

                for chunk in openai_chat_stream(
                    params={
                        "model": self.model,
                        "messages": [m.to_dict() for m in messages],
                        "stream": True,
                        **self.api_kwargs,
                    }
                ):
                    if chunk:
                        yield openai_util.convert_to_openai_object(json.loads(chunk))
            except Exception as e:
                logger.exception(e)
                logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                exit(1)
        else:
            yield from openai.ChatCompletion.create(
                model=self.model,
                messages=[m.to_dict() for m in messages],
                stream=True,
                **self.api_kwargs,
            )

    def parsed_response(self, messages: List[Message]) -> str:
        logger.debug("---------- OpenAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: OpenAIObject = self.invoke_model(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        # logger.debug(f"OpenAI response type: {type(response)}")
        # logger.debug(f"OpenAI response: {response}")

        # -*- Parse response
        response_message = response.choices[0].message
        response_role = response_message.get("role")
        response_content = response_message.get("content")
        response_function_call = response_message.get("function_call")

        # -*- Create assistant message
        assistant_message = Message(
            role=response_role or "assistant",
            content=response_content,
        )
        if response_function_call is not None and isinstance(response_function_call, OpenAIObject):
            assistant_message.function_call = response_function_call.to_dict()

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        response_usage = response.usage
        prompt_tokens = response_usage.get("prompt_tokens")
        if prompt_tokens is not None:
            assistant_message.metrics["prompt_tokens"] = prompt_tokens
            if "prompt_tokens" not in self.metrics:
                self.metrics["prompt_tokens"] = prompt_tokens
            else:
                self.metrics["prompt_tokens"] += prompt_tokens
        completion_tokens = response_usage.get("completion_tokens")
        if completion_tokens is not None:
            assistant_message.metrics["completion_tokens"] = completion_tokens
            if "completion_tokens" not in self.metrics:
                self.metrics["completion_tokens"] = completion_tokens
            else:
                self.metrics["completion_tokens"] += completion_tokens
        total_tokens = response_usage.get("total_tokens")
        if total_tokens is not None:
            assistant_message.metrics["total_tokens"] = total_tokens
            if "total_tokens" not in self.metrics:
                self.metrics["total_tokens"] = total_tokens
            else:
                self.metrics["total_tokens"] += total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Return content if present, otherwise run function call
        if assistant_message.content is not None:
            return assistant_message.content

        # -*- Parse and run function call
        if assistant_message.function_call is not None and self.run_function_calls:
            _function_name = assistant_message.function_call.get("name")
            _function_arguments_str = assistant_message.function_call.get("arguments")
            if _function_name is not None:
                # Get function call
                function_call = self.get_function_call(name=_function_name, arguments=_function_arguments_str)
                if function_call is None:
                    return "Something went wrong, please try again."

                if self.function_call_stack is None:
                    self.function_call_stack = []

                # -*- Check function call limit
                if len(self.function_call_stack) > self.function_call_limit:
                    return f"Function call limit ({self.function_call_limit}) exceeded."

                # -*- Run function call
                self.function_call_stack.append(function_call)
                function_call_timer = Timer()
                function_call_timer.start()
                function_call.run()
                function_call_timer.stop()
                function_call_message = Message(
                    role="function",
                    name=function_call.function.name,
                    content=function_call.result,
                    metrics={"time": function_call_timer.elapsed},
                )
                messages.append(function_call_message)
                if "function_call_times" not in self.metrics:
                    self.metrics["function_call_times"] = {}
                if function_call.function.name not in self.metrics["function_call_times"]:
                    self.metrics["function_call_times"][function_call.function.name] = []
                self.metrics["function_call_times"][function_call.function.name].append(function_call_timer.elapsed)

                # -*- Get new response using result of function call
                final_response = ""
                if self.show_function_calls:
                    final_response += f"Running: {function_call.get_call_str()}\n\n"
                final_response += self.parsed_response(messages=messages)
                return final_response
        logger.debug("---------- OpenAI Response End ----------")
        return "Something went wrong, please try again."

    def response_message(self, messages: List[Message]) -> Dict:
        logger.debug("---------- OpenAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: OpenAIObject = self.invoke_model(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        # logger.debug(f"OpenAI response type: {type(response)}")
        # logger.debug(f"OpenAI response: {response}")

        # -*- Parse response
        response_message = response.choices[0].message
        response_role = response_message.get("role")
        response_content = response_message.get("content")
        response_function_call = response_message.get("function_call")

        # -*- Create assistant message
        assistant_message = Message(
            role=response_role or "assistant",
            content=response_content,
        )
        if response_function_call is not None and isinstance(response_function_call, OpenAIObject):
            assistant_message.function_call = response_function_call.to_dict()

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        response_usage = response.usage
        prompt_tokens = response_usage.get("prompt_tokens")
        if prompt_tokens is not None:
            assistant_message.metrics["prompt_tokens"] = prompt_tokens
            if "prompt_tokens" not in self.metrics:
                self.metrics["prompt_tokens"] = prompt_tokens
            else:
                self.metrics["prompt_tokens"] += prompt_tokens
        completion_tokens = response_usage.get("completion_tokens")
        if completion_tokens is not None:
            assistant_message.metrics["completion_tokens"] = completion_tokens
            if "completion_tokens" not in self.metrics:
                self.metrics["completion_tokens"] = completion_tokens
            else:
                self.metrics["completion_tokens"] += completion_tokens
        total_tokens = response_usage.get("total_tokens")
        if total_tokens is not None:
            assistant_message.metrics["total_tokens"] = total_tokens
            if "total_tokens" not in self.metrics:
                self.metrics["total_tokens"] = total_tokens
            else:
                self.metrics["total_tokens"] += total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Return response
        response_message_dict = response_message.to_dict_recursive()
        logger.debug("---------- OpenAI Response End ----------")
        return response_message_dict

    def parsed_response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- OpenAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        assistant_message_function_name = ""
        assistant_message_function_arguments_str = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_model_stream(messages=messages):
            # logger.debug(f"OpenAI response type: {type(response)}")
            # logger.debug(f"OpenAI response: {response}")
            completion_tokens += 1

            # -*- Parse response
            response_delta = response.choices[0].delta
            response_content = response_delta.get("content")
            response_function_call = response_delta.get("function_call")

            # -*- Return content if present, otherwise get function call
            if response_content is not None:
                assistant_message_content += response_content
                yield response_content

            # -*- Parse function call
            if response_function_call is not None:
                _function_name_stream = response_function_call.get("name")
                if _function_name_stream is not None:
                    assistant_message_function_name += _function_name_stream
                _function_args_stream = response_function_call.get("arguments")
                if _function_args_stream is not None:
                    assistant_message_function_arguments_str += _function_args_stream

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role="assistant")
        # -*- Add content to assistant message
        if assistant_message_content != "":
            assistant_message.content = assistant_message_content
        # -*- Add function call to assistant message
        if assistant_message_function_name != "":
            assistant_message.function_call = {
                "name": assistant_message_function_name,
                "arguments": assistant_message_function_arguments_str,
            }

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        # TODO: compute prompt tokens
        prompt_tokens = 0
        assistant_message.metrics["prompt_tokens"] = prompt_tokens
        if "prompt_tokens" not in self.metrics:
            self.metrics["prompt_tokens"] = prompt_tokens
        else:
            self.metrics["prompt_tokens"] += prompt_tokens
        logger.debug(f"Estimated completion tokens: {completion_tokens}")
        assistant_message.metrics["completion_tokens"] = completion_tokens
        if "completion_tokens" not in self.metrics:
            self.metrics["completion_tokens"] = completion_tokens
        else:
            self.metrics["completion_tokens"] += completion_tokens
        total_tokens = prompt_tokens + completion_tokens
        assistant_message.metrics["total_tokens"] = total_tokens
        if "total_tokens" not in self.metrics:
            self.metrics["total_tokens"] = total_tokens
        else:
            self.metrics["total_tokens"] += total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function call
        if assistant_message.function_call is not None and self.run_function_calls:
            _function_name = assistant_message.function_call.get("name")
            _function_arguments_str = assistant_message.function_call.get("arguments")
            if _function_name is not None:
                # Get function call
                function_call: Optional[FunctionCall] = self.get_function_call(
                    name=_function_name, arguments=_function_arguments_str
                )
                if function_call is None:
                    return "Something went wrong, please try again."

                if self.function_call_stack is None:
                    self.function_call_stack = []

                # -*- Check function call limit
                if len(self.function_call_stack) > self.function_call_limit:
                    return f"Function call limit ({self.function_call_limit}) exceeded."

                # -*- Run function call
                self.function_call_stack.append(function_call)
                if self.show_function_calls:
                    yield f"Running: {function_call.get_call_str()}\n\n"
                function_call_timer = Timer()
                function_call_timer.start()
                function_call.run()
                function_call_timer.stop()
                function_call_message = Message(
                    role="function",
                    name=function_call.function.name,
                    content=function_call.result,
                    metrics={"time": function_call_timer.elapsed},
                )
                messages.append(function_call_message)
                if "function_call_times" not in self.metrics:
                    self.metrics["function_call_times"] = {}
                if function_call.function.name not in self.metrics["function_call_times"]:
                    self.metrics["function_call_times"][function_call.function.name] = []
                self.metrics["function_call_times"][function_call.function.name].append(function_call_timer.elapsed)

                # -*- Yield new response using result of function call
                yield from self.parsed_response_stream(messages=messages)
        logger.debug("---------- OpenAI Response End ----------")

    def response_delta(self, messages: List[Message]) -> Iterator[Dict]:
        logger.debug("---------- OpenAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        assistant_message_function_name = ""
        assistant_message_function_arguments_str = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_model_stream(messages=messages):
            # logger.debug(f"OpenAI response type: {type(response)}")
            # logger.debug(f"OpenAI response: {response}")
            completion_tokens += 1

            # -*- Parse response
            response_delta = response.choices[0].delta

            # -*- Read content
            response_content = response_delta.get("content")
            if response_content is not None:
                assistant_message_content += response_content

            # -*- Read function call
            response_function_call = response_delta.get("function_call")
            if response_function_call is not None:
                _function_name_stream = response_function_call.get("name")
                if _function_name_stream is not None:
                    assistant_message_function_name += _function_name_stream
                _function_args_stream = response_function_call.get("arguments")
                if _function_args_stream is not None:
                    assistant_message_function_arguments_str += _function_args_stream

            yield response_delta.to_dict_recursive()
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role="assistant")
        # -*- Add content to assistant message
        if assistant_message_content != "":
            assistant_message.content = assistant_message_content
        # -*- Add function call to assistant message
        if assistant_message_function_name != "":
            assistant_message.function_call = {
                "name": assistant_message_function_name,
                "arguments": assistant_message_function_arguments_str,
            }

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        # TODO: compute prompt tokens
        prompt_tokens = 0
        assistant_message.metrics["prompt_tokens"] = prompt_tokens
        if "prompt_tokens" not in self.metrics:
            self.metrics["prompt_tokens"] = prompt_tokens
        else:
            self.metrics["prompt_tokens"] += prompt_tokens
        logger.debug(f"Estimated completion tokens: {completion_tokens}")
        assistant_message.metrics["completion_tokens"] = completion_tokens
        if "completion_tokens" not in self.metrics:
            self.metrics["completion_tokens"] = completion_tokens
        else:
            self.metrics["completion_tokens"] += completion_tokens

        total_tokens = prompt_tokens + completion_tokens
        assistant_message.metrics["total_tokens"] = total_tokens
        if "total_tokens" not in self.metrics:
            self.metrics["total_tokens"] = total_tokens
        else:
            self.metrics["total_tokens"] += total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()
        logger.debug("---------- OpenAI Response End ----------")

    def run_function_call(self, function_call: Dict[str, Any]) -> Optional[Message]:
        _function_name = function_call.get("name")
        _function_arguments_str = function_call.get("arguments")
        if _function_name is not None:
            function_call_obj: Optional[FunctionCall] = self.get_function_call(
                name=_function_name, arguments=_function_arguments_str
            )
            if function_call_obj is None:
                return None

            # -*- Run function call
            function_call_timer = Timer()
            function_call_timer.start()
            function_call_obj.run()
            function_call_timer.stop()
            function_call_message = Message(
                role="function",
                name=function_call_obj.function.name,
                content=function_call_obj.result,
                metrics={"time": function_call_timer.elapsed},
            )
            return function_call_message
        return None
