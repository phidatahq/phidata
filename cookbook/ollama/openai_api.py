from phi.assistant import Assistant
from phi.llm.ollama import OllamaOpenAI

assistant = Assistant(
    llm=OllamaOpenAI(model="tinyllama"),
    system_prompt="Who are you and who made you?"
)
assistant.print_response()
