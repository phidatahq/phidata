from phi.agent import Agent
from phi.model.google import Gemini

agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
)

# Please download a sample audio file to test this Agent
agent.print_response(
    "Tell me about this audio",
    audio={"data": "cookbook/providers/google/sample_audio.mp3"},
    stream=True,
)
