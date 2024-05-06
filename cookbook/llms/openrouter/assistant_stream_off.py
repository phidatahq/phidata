from phi.assistant import Assistant
from phi.llm.openrouter import OpenRouter

assistant = Assistant(
    llm=OpenRouter(model="mistralai/mistral-7b-instruct:free"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a 2 sentence quick and healthy breakfast recipe.", markdown=True, stream=False)
