from phi.assistant import Assistant
from phi.llm.ollama import Hermes

assistant = Assistant(
    llm=Hermes(model="adrienbrault/nous-hermes2pro:Q8_0"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
