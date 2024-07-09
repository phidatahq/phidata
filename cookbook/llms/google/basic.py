from phi.assistant import Assistant
from phi.llm.google import Gemini

assistant = Assistant(
    llm=Gemini(model="gemini-1.5-flash"),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
