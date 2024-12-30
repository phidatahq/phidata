from pathlib import Path

from phi.agent import Agent
from phi.model.ollama import Ollama

agent = Agent(
    model=Ollama(id="llama3.2-vision"),
    markdown=True,
)

image_path = Path(__file__).parent.joinpath("super-agents.png")
agent.print_response(
    "Write a 3 sentence fiction story about the image",
    images=[str(image_path)],
)
