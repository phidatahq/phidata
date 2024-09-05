from os import getenv
from typing import Optional, List, Iterator

from phi.llm.message import Message
from phi.llm.openai.like import OpenAILike
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk


class Fireworks(OpenAILike):
    name: str = "Fireworks"
    model: str = "accounts/fireworks/models/firefunction-v1"
    api_key: Optional[str] = getenv("FIREWORKS_API_KEY")
    base_url: str = "https://api.fireworks.ai/inference/v1"

    def invoke_stream(self, messages: List[Message]) -> Iterator[ChatCompletionChunk]:
        yield from self.get_client().chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],  # type: ignore
            stream=True,
            **self.api_kwargs,
        )  # type: ignore
