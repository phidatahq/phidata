from phi.assistant import Assistant
from phi.llm.mistral import Mistral

assistant = Assistant(
    llm=Mistral(model="open-mixtral-8x22b"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
