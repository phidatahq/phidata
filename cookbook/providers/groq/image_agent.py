from phi.agent import Agent
from phi.model.groq import Groq

agent = Agent(model=Groq(id="llama-3.2-90b-vision-preview"))

agent.print_response(
    "Tell me about this image",
    images=[
        "https://upload.wikimedia.org/wikipedia/commons/f/f2/LPU-v1-die.jpg",
    ],
    stream=True,
)
