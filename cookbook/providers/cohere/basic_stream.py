from phi.agent import Agent
from phi.model.cohere import CohereChat

agent = Agent(
    model=CohereChat(model="command-r"),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
agent.print_response("Share a quick healthy breakfast recipe.", markdown=True, stream=False)
