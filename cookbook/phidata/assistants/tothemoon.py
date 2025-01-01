from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

assistant = Assistant(
    llm=OpenAIChat(model="gpt-4o"),
    description="You are a rocket scientist",
)
assistant.print_response("write a plan to go to the moon stp by step", markdown=True)
