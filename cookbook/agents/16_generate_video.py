from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.models_labs import ModelsLabs

agent = Agent(
    name="Video Generation Agent",
    agent_id="video-generation-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ModelsLabs()],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
    instructions=[
        "You are an agent designed to generate videos using the VideoGen API.",
        "When asked to generate a video, use the generate_video function from the VideoGenTools.",
        "Only pass the 'prompt' parameter to the generate_video function unless specifically asked for other parameters.",
        "The VideoGen API returns an status and eta value, also display it in your response.",
        "After generating the video, return only the video URL from the API response.",
    ],
    system_message="Do not modify any default parameters of the generate_video function unless explicitly specified in the user's request.",
)

agent.print_response("Generate a video of a cat playing with a ball")
