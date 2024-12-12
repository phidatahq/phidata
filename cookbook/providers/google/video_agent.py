from phi.agent import Agent
from phi.model.google import Gemini

agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
)

# Please download "GreatRedSpot.mp4" using wget https://storage.googleapis.com/generativeai-downloads/images/GreatRedSpot.mp4
agent.print_response(
    "Tell me about this video",
    videos=[
        "cookbook/providers/google/GreatRedSpot.mp4",
    ],
    stream=True,
)
