from phi.assistant import Assistant
from phi.llm.ollama import Ollama

assistant = Assistant(
    llm=Ollama(),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
assistant.print_response("Share a quick healthy breakfast recipe.", stream=False, markdown=True)
