from phi.agent import Agent
from phi.tools.youtube_tools import YouTubeTools

agent = Agent(
    tools=[YouTubeTools()],
    show_tool_calls=True,
    description="You are a YouTube agent. Obtain the timestamps for a YouTube video based on captions.",
)
agent.print_response("Add timestamps to this video https://youtu.be/M5tx7VI-LFA?si=6yUBejy49sffm8e5", markdown=True)
