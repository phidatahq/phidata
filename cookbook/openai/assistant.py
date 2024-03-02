from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4-turbo-preview"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a 2 sentence quick healthy breakfast recipe.", markdown=True)
