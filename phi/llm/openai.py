from typing import Optional, List, Iterator, Dict, Any

from phi.llm.base import LLM
from phi.llm.schemas import Message
from phi.utils.log import logger

try:
    from openai import ChatCompletion  # noqa: F401
    from openai.openai_object import OpenAIObject  # noqa: F401
except ImportError:
    raise ImportError("`openai` not installed")


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
            logger.debug(f"{m.role.upper()}: {m.content}")

        response: OpenAIObject = ChatCompletion.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            **self.api_kwargs(),
        )
        # logger.debug(f"OpenAI response type: {type(response)}")
        # logger.debug(f"OpenAI response: {response}")

        # Update metrics
        usage = response["usage"]
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]
        total_tokens = usage["total_tokens"]

        if "prompt_tokens" in self.metrics:
            self.metrics["prompt_tokens"] += prompt_tokens
        else:
            self.metrics["prompt_tokens"] = prompt_tokens
        if "completion_tokens" in self.metrics:
            self.metrics["completion_tokens"] += completion_tokens
        else:
            self.metrics["completion_tokens"] = completion_tokens
        if "total_tokens" in self.metrics:
            self.metrics["total_tokens"] += total_tokens
        else:
            self.metrics["total_tokens"] = total_tokens
        if "prompts" in self.metrics:
            self.metrics["prompts"] += 1
        else:
            self.metrics["prompts"] = 1

        response_content = response.choices[0].message.get("content")
        response_function_call = response.choices[0].message.get("function_call")
        if response_content is not None:
            # logger.debug(f"response_content type: {type(response_content)}")
            # logger.debug(f"response_content: {response_content}")
            return response_content
        if response_function_call is not None:
            # logger.debug(f"response_function_call type: {type(response_function_call)}")
            # logger.debug(f"response_function_call: {response_function_call}")
            _function_name = response_function_call.get("name")
            _function_arguments_str = response_function_call.get("arguments")
            if _function_name is not None:
                function_call = self.get_function_call(name=_function_name, arguments=_function_arguments_str)
                if function_call is None:
                    return "Something went wrong, please try again."

                if self.function_call_stack is None:
                    self.function_call_stack = []
                self.function_call_stack.append(function_call)
                function_call.run()
                next_message = Message(
                    role="function",
                    name=function_call.function.name,
                    content=function_call.result,
                    # function_call={
                    #     "name": _function_name,
                    #     "arguments": _function_arguments_str,
                    # }
                    # content=remove_indent(
                    #     f"""
                    # You can use the result of the following function call to continue the conversation:
                    # function_call = {function_call.get_call_str()}
                    # function_call_result = {function_call.result}
                    # """
                    # ),
                )
                messages.append(next_message)
                final_response = ""
                if self.show_function_calls:
                    final_response += f"Running function: {function_call.get_call_str()}\n\n"
                final_response += self.response(messages=messages)
                return final_response

        logger.debug("---------- OpenAI Response End ----------")
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- OpenAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            logger.debug(f"{m.role.upper()}: {m.content}")

        _function_name = ""
        _function_arguments_str = ""
        completion_tokens = 0
        for response in ChatCompletion.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            stream=True,
            **self.api_kwargs(),
        ):
            # logger.debug(f"OpenAI response type: {type(response)}")
            # logger.debug(f"OpenAI response: {response}")
            completion_tokens += 1

            response_content = response.choices[0].delta.get("content")
            response_function_call = response.choices[0].delta.get("function_call")
            if response_content:
                # logger.debug(f"response_content type: {type(response_content)}")
                # logger.debug(f"response_content: {response_content}")
                yield response_content
            if response_function_call:
                # logger.debug(f"response_function_call type: {type(response_function_call)}")
                # logger.debug(f"response_function_call: {response_function_call}")
                _function_name_stream = response_function_call.get("name")
                if _function_name_stream is not None:
                    _function_name += _function_name_stream
                _function_args_stream = response_function_call.get("arguments")
                if _function_args_stream is not None:
                    _function_arguments_str += _function_args_stream

        logger.debug(f"Estimated completion tokens: {completion_tokens}")
        # Update metrics
        if "completion_tokens" in self.metrics:
            self.metrics["completion_tokens"] += completion_tokens
        else:
            self.metrics["completion_tokens"] = completion_tokens
        if "prompts" in self.metrics:
            self.metrics["prompts"] += 1
        else:
            self.metrics["prompts"] = 1

        if _function_name is not None and _function_name != "":
            function_call = self.get_function_call(name=_function_name, arguments=_function_arguments_str)
            if function_call is None:
                return "Something went wrong, please try again."

            if self.function_call_stack is None:
                self.function_call_stack = []
            self.function_call_stack.append(function_call)
            if self.show_function_calls:
                yield f"Running function: {function_call.get_call_str()}\n\n"
            function_call.run()
            next_message = Message(
                role="function",
                name=function_call.function.name,
                content=function_call.result,
                # role="system",
                # content=remove_indent(
                #     f"""
                # You can use the result of the following function call to continue the conversation:
                # function_call = {function_call.get_call_str()}
                # function_call_result = {function_call.result}
                # """
                # ),
            )
            messages.append(next_message)
            yield from self.response_stream(messages=messages)
        logger.debug("---------- OpenAI Response End ----------")
