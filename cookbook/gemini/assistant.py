from phi.assistant import Assistant
from phi.llm.gemini import Gemini

assistant = Assistant(
    llm=Gemini(model="gemini-1.0-pro-vision"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a 2 sentence quick healthy breakfast recipe.", markdown=True)
