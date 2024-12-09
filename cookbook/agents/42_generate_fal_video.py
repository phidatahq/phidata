from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.fal import Fal

fal_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[Fal()],
    description="You are an AI agent that can generate videos using the 'fal' API.",
    instructions=[
        "When the user asks you to create a video, use the `run` tool to create the video.",
        "Return the URL as raw to the user.",
        "Don't convert video URL to markdown or anything else.",
        "Use `fal-ai/hunyuan-video` model by default.",
    ],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
)

fal_agent.print_response("Generate video of ballon in the ocean")
