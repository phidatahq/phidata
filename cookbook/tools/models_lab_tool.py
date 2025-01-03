"""Run `pip install requests` to install dependencies."""

from phi.agent import Agent
from phi.tools.models_labs import ModelsLabs

# Create an Agent with the ModelsLabs tool
agent = Agent(tools=[ModelsLabs()], name="ModelsLabs Agent")

agent.print_response("Generate a video of a beautiful sunset over the ocean", markdown=True)
