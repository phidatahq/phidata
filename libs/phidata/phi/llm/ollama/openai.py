from phi.llm.openai.like import OpenAILike


class OllamaOpenAI(OpenAILike):
    name: str = "Ollama"
    model: str = "openhermes"
    api_key: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
