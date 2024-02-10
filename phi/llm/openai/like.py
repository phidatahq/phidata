from typing import Optional
from phi.llm.openai.chat import OpenAIChat


class OpenAILike(OpenAIChat):
    name: str = "OpenAILike"
    model: Optional[str] = None
    phi_proxy: bool = False
