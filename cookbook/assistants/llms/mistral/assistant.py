import os
from phi.assistant import Assistant
from phi.llm.mistral import MistralChat

assistant = Assistant(
    llm=MistralChat(
        model="open-mixtral-8x22b",
        api_key=os.environ["MISTRAL_API_KEY"],
    ),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
