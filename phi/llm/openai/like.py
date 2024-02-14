from phi.llm.openai.chat import OpenAIChat


class OpenAILike(OpenAIChat):
    name: str = "OpenAILike"
    model: str = "not-provided"
    api_key: str = "not-provided"
    phi_proxy: bool = False
