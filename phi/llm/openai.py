from typing import Optional, List, Iterator

from phi.llm.base import LLM


class OpenAIChat(LLM):
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
        return response["choices"][0]["text"]

    def streaming_response(self, messages: List) -> Iterator[str]:
        try:
            from openai import ChatCompletion  # noqa: F401
        except ImportError:
            raise ImportError("`openai` not installed")

        for delta in ChatCompletion.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True,
        ):
            yield delta.choices[0].delta.get("content", "")
