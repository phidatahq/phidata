from typing import Optional, List, Iterator, Dict, Any

from phi.llm.base import LLM
from phi.llm.schemas import Message, FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer

try:
    from openai import ChatCompletion  # noqa: F401
    from openai.openai_object import OpenAIObject  # noqa: F401
except ImportError:
    logger.error("`openai` not installed")
    raise


class OpenAIChat(LLM):
    name: str = "OpenAIChat"
    model: str = "gpt-3.5-turbo-16k"
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

    def api_kwargs(self) -> dict:
        kwargs: Dict[str, Any] = {}
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens
        if self.temperature:
            kwargs["temperature"] = self.temperature
        if self.functions:
            kwargs["functions"] = [f.to_dict() for f in self.functions.values()]
            if self.function_call is not None:
                kwargs["function_call"] = self.function_call
        return kwargs

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- OpenAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: OpenAIObject = ChatCompletion.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            **self.api_kwargs(),
        )
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
        if assistant_message.function_call is not None:
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
                final_response += self.response(messages=messages)
                return final_response
        logger.debug("---------- OpenAI Response End ----------")
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- OpenAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content="")
        # -*- Add assistant message to messages
        messages.append(assistant_message)

        _function_name = ""
        _function_arguments_str = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for response in ChatCompletion.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            stream=True,
            **self.api_kwargs(),
        ):
            # logger.debug(f"OpenAI response type: {type(response)}")
            # logger.debug(f"OpenAI response: {response}")
            completion_tokens += 1

            # -*- Parse response
            response_delta = response.choices[0].delta
            response_content = response_delta.get("content")
            response_function_call = response_delta.get("function_call")

            # -*- Return content if present, otherwise get function call
            if response_content is not None:
                assistant_message.content += response_content
                yield response_content

            # -*- Parse function call
            if response_function_call is not None:
                _function_name_stream = response_function_call.get("name")
                if _function_name_stream is not None:
                    _function_name += _function_name_stream
                _function_args_stream = response_function_call.get("arguments")
                if _function_args_stream is not None:
                    _function_arguments_str += _function_args_stream
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

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

        # -*- Parse and run function call
        if _function_name is not None and _function_name != "":
            # Update assistant message to reflect function call
            if assistant_message.content == "":
                assistant_message.content = None
            assistant_message.function_call = {
                "name": _function_name,
                "arguments": _function_arguments_str,
            }
            assistant_message.log()

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
            yield from self.response_stream(messages=messages)
        logger.debug("---------- OpenAI Response End ----------")
