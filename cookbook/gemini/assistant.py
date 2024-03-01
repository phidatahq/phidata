from os import getenv

import vertexai
from phi.assistant import Assistant
from phi.llm.gemini import Gemini

# *********** Initialize VertexAI ***********
vertexai.init(project=getenv("PROJECT_ID"), location=getenv("LOCATION"))

assistant = Assistant(
    llm=Gemini(model="gemini-1.0-pro-vision"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
