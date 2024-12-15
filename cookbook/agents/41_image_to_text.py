from pathlib import Path

from phi.agent import Agent
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
)

image_path = Path(__file__).parent.joinpath("multimodal-agents.jpg")
agent.print_response(
    "Write a 3 sentence fiction story about the image",
    images=[str(image_path)],
)
