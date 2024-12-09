from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.hunyuan_video import HunyuanVideo

video_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[HunyuanVideo()],
    description="You are an AI agent that can generate videos using the ModelsLabs API.",
    instructions=[
        "When the user asks you to create a video, use the `generate_video` tool to create the video.",
        "Return the video URL as raw to the user.",
        "Don't convert video URL to markdown or anything else.",
    ],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
)

video_agent.print_response("Generate a video of a cat playing with a ball")
