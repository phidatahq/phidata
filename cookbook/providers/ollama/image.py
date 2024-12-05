from pathlib import Path

from phi.agent import Agent
from phi.model.ollama import Ollama

agent = Agent(
    model=Ollama(id="llava"),
    markdown=True,
)

image_path = Path(__file__).parent.joinpath("test-image.jpg")
agent.print_response(
    "What's in this image, describe in 1 sentence",
    images=[str(image_path)],
)
