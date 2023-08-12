from typing import Optional, List, Iterator, Dict, Any

from phi.llm.base import LLM
from phi.llm.schemas import Message
from phi.utils.log import logger

try:
    from openai import ChatCompletion  # noqa: F401
    from openai.openai_object import OpenAIObject  # noqa: F401
except ImportError:
    raise ImportError("`openai` not installed")

conversation_function = {
    "name": "get_chat_history",
    "description": "Returns the chat history as a list of dictionaries.",
    "parameters": {
        "type": "object",
        "properties": {
            "num_messages": {
                "type": "integer",
                "description": "number of messages to return",
            },
        },
    },
}


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
        kwargs["functions"] = [conversation_function]
        # if self.functions:
        #     kwargs["functions"] = [f.model_dump(exclude_none=True) for f in self.functions]
        #     if self.function_call:
        #         kwargs["function_call"] = self.function_call
        return kwargs

    def response(self, messages: List[Message]) -> OpenAIObject:
        response = ChatCompletion.create(
            model=self.model,
            messages=[m.model_dump(exclude_none=True) for m in messages],
            **self.api_kwargs(),
        )
        logger.debug(f"OpenAI response type: {type(response)}")
        logger.debug(f"OpenAI response: {response}")

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

        # Return response
        # return response["choices"][0]["message"]["content"]
        return response

    def response_stream(self, messages: List[Message]) -> Iterator[OpenAIObject]:
        completion_tokens = 0
        for response in ChatCompletion.create(
            model=self.model,
            messages=[m.model_dump(exclude_none=True) for m in messages],
            stream=True,
            **self.api_kwargs(),
        ):
            logger.debug(f"OpenAI response type: {type(response)}")
            logger.debug(f"OpenAI response: {response}")
            completion_tokens += 1
            yield response
            # yield delta.choices[0].delta.get("content", "")

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
