from phi.assistant import Assistant
from phi.llm.openai.like import OpenAILike

assistant = Assistant(
    llm=OpenAILike(base_url="http://localhost:8000/v1"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a 2 sentence quick healthy breakfast recipe.", markdown=True)
