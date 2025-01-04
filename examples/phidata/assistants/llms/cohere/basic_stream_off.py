from phi.assistant import Assistant
from phi.llm.cohere import CohereChat

assistant = Assistant(
    llm=CohereChat(model="command-r"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True, stream=False)
