from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4-turbo", max_tokens=500, temperature=0.3),
    description="You provide 15 minute healthy recipes.",
)
assistant.print_response("Share a breakfast recipe.", markdown=True)
