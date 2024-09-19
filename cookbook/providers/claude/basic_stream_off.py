from phi.agent import Agent
from phi.model.anthropic import Claude

agent = Agent(
    model=Claude(model="claude-3-5-sonnet-20240620"),
    description="You help people with their health and fitness goals.",
)
agent.print_response("Share a quick healthy breakfast recipe.", markdown=True, stream=False)
