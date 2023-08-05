from typing import Optional, List, Iterator

from phi.llm.base import LLM
from phi.utils.log import logger


class OpenAIChat(LLM):
    name: str = "OpenAIChat"
    model: str = "gpt-3.5-turbo-16k"
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

    def response(self, messages: List) -> str:
        try:
            from openai import ChatCompletion  # noqa: F401
        except ImportError:
            raise ImportError("`openai` not installed")

        response = ChatCompletion.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
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

        # Return response
        return response["choices"][0]["message"]["content"]

    def response_stream(self, messages: List) -> Iterator[str]:
        try:
            from openai import ChatCompletion  # noqa: F401
        except ImportError:
            raise ImportError("`openai` not installed")

        completion_tokens = 0
        for delta in ChatCompletion.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True,
        ):
            # logger.debug(f"OpenAI response type: {type(delta)}")
            # logger.debug(f"OpenAI response: {delta}")
            completion_tokens += 1
            yield delta.choices[0].delta.get("content", "")

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
