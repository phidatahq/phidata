from phi.agent import Agent
from phi.llm.openai import OpenAIChat
from phi.tools.lumalab import LumaLab

"""Create an agent specialized for Luma AI video generation"""

luma_agent = Agent(
    name="Luma Video Agent",
    agent_id="luma-video-agent",
    llm=OpenAIChat(model="gpt-4o"),
    tools=[LumaLab()],  # Using the LumaLab tool we created
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
    instructions=[
        "You are an agent designed to generate videos using the Luma AI API.",
        "When asked to generate a video, use the generate_video function from the LumaLab toolkit.",
        "Only pass the required parameters to the generate_video function unless specifically asked for other parameters.",
        "The default parameters are:",
        "- loop: False",
        "- aspect_ratio: '16:9'",
        "- keyframes: None",
        "After generating the video, display the video URL in markdown format.",
        "If the video generation is async (wait_for_completion=False), inform the user about the generation ID.",
        "If any errors occur during generation, clearly communicate them to the user.",
    ],
    system_message=(
        "Do not modify any default parameters of the generate_video function "
        "unless explicitly specified in the user's request. Always provide clear "
        "feedback about the video generation status."
    ),
)

luma_agent.run("Generate a video of a sunset over a peaceful ocean with gentle waves")



