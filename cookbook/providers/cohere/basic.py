from phi.assistant import Assistant
from phi.model.cohere import CohereChat

assistant = Assistant(
    model=CohereChat(model="command-r"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
