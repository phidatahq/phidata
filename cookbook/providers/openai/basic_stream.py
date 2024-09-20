from phi.agent import Agent
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    description="You help people with their health and fitness goals.",
)

agent.print_response("Share a healthy breakfast recipe", stream=True)
