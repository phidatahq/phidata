from phi.llm.openai.chat import OpenAIChat


class OllamaOpenAI(OpenAIChat):
    name: str = "Ollama"
    model: str = "openhermes"
    api_key: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
    phi_proxy: bool = False
