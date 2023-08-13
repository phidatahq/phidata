import json
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
            kwargs["functions"] = [f.to_dict() for f in self.functions]
            if self.function_call is not None:
                kwargs["function_call"] = self.function_call
        return kwargs

    def response(self, messages: List[Message]) -> str:
        response: OpenAIObject = ChatCompletion.create(
            model=self.model,
            messages=[m.model_dump(exclude_none=True) for m in messages],
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

        content = response.choices[0].message.get("content")
        function_call = response.choices[0].message.get("function_call")
        if content is not None:
            # logger.debug(f"content type: {type(content)}")
            # logger.debug(f"content: {content}")
            return content
        if function_call is not None:
            # logger.debug(f"function_call type: {type(function_call)}")
            # logger.debug(f"function_call: {function_call}")
            function_name = function_call.get("name")
            function_arguments_str = function_call.get("arguments")
            function_arguments = {}
            if function_name is not None:
                if function_arguments_str is not None:
                    try:
                        function_arguments = json.loads(function_arguments_str)
                    except Exception as e:
                        logger.warning(f"Could not decode function arguments {function_arguments_str}: {e}")
                        return "Something went wrong, please try again."
                response_content = "Calling function: {}({})".format(
                    function_name, ", ".join("{}={}".format(k, v) for k, v in function_arguments.items())
                )
                # ... call function here ...
                return response_content
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        function_name = ""
        function_arguments = {}
        function_arguments_str = ""

        completion_tokens = 0
        for response in ChatCompletion.create(
            model=self.model,
            messages=[m.model_dump(exclude_none=True) for m in messages],
            stream=True,
            **self.api_kwargs(),
        ):
            # logger.debug(f"OpenAI response type: {type(response)}")
            # logger.debug(f"OpenAI response: {response}")
            completion_tokens += 1

            content = response.choices[0].delta.get("content")
            function_call = response.choices[0].delta.get("function_call")
            if content:
                # logger.debug(f"content type: {type(content)}")
                # logger.debug(f"content: {content}")
                yield content
            if function_call:
                # logger.debug(f"function_call type: {type(function_call)}")
                # logger.debug(f"function_call: {function_call}")
                _function_name = function_call.get("name")
                if _function_name is not None:
                    function_name += _function_name
                _function_args = function_call.get("arguments")
                if _function_args is not None:
                    function_arguments_str += _function_args

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

        if function_name is not None and function_name != "":
            if function_arguments_str is not None and function_arguments_str != "":
                try:
                    function_arguments = json.loads(function_arguments_str)
                except Exception as e:
                    logger.warning(f"Could not decode function arguments {function_arguments_str}: {e}")
                    return "Something went wrong, please try again."
            function_call_str = "Calling function: {}({})".format(
                function_name, ", ".join("{}={}".format(k, v) for k, v in function_arguments.items())
            )
            yield function_call_str
            # yield from ... call function here ...
