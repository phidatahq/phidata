"""Run `pip install openai` to install dependencies."""

from phi.agent import Agent
from phi.tools.dalle import Dalle

# Create an Agent with the DALL-E tool
agent = Agent(tools=[Dalle()], name="DALL-E Image Generator")

# Example 1: Generate a basic image with default settings
agent.print_response("Generate an image of a futuristic city with flying cars and tall skyscrapers", markdown=True)

# Example 2: Generate an image with custom settings
custom_dalle = Dalle(model="dall-e-3", size="1792x1024", quality="hd", style="natural")

agent_custom = Agent(
    tools=[custom_dalle],
    name="Custom DALL-E Generator",
    show_tool_calls=True,
)

agent_custom.print_response("Create a panoramic nature scene showing a peaceful mountain lake at sunset", markdown=True)
