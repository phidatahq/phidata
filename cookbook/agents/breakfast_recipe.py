from phi.agent import Agent
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4-turbo"),
    description="Share 15 minute healthy recipes.",
    markdown=True,
)
agent.print_response("Share a breakfast recipe.", stream=True)
