from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4-turbo-preview"),
)
assistant.cli_app(markdown=True)
