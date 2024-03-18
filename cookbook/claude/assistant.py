from phi.assistant import Assistant
from phi.llm.anthropic import Claude

assistant = Assistant(
    llm=Claude(),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
