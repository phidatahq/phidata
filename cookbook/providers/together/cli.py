from phi.agent import Agent
from phi.model.together import Together

agent = Agent(
    model=Together(id="mistralai/Mixtral-8x7B-Instruct-v0.1"),
    description="You help people with their health and fitness goals.",
    markdown=True,
    show_tool_calls=True,
)

agent.cli_app(markdown=True, stream=False)
