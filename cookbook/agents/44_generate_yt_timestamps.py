from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.youtube_tools import YouTubeTools

agent = Agent(
    name="YouTube Timestamps Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YouTubeTools()],
    show_tool_calls=True,
    instructions=[
        "You are a YouTube agent. First check the length of the video. Then get the detailed timestamps for a YouTube video corresponding to correct timestamps.",
        "Don't hallucinate timestamps.",
        "Make sure to return the timestamps in the format of `[start_time, end_time, summary]`.",
    ],
)
agent.print_response(
    "Get the detailed timestamps for this video https://www.youtube.com/watch?v=M5tx7VI-LFA", markdown=True
)
