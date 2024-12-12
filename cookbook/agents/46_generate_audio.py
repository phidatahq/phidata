from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.eleven_labs_tools import ElevenLabsTools

audio_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[ElevenLabsTools()],
    description="You are an AI agent that can generate audio using the ElevenLabs API.",
    instructions=[
        "When the user asks you to generate audio, use the `generate_audio` tool to generate the audio.",
        "You'll pass the text to generate audio from to the tool.",
        "Return the audio file name in your response. Don't convert it to markdown.",
        "The audio should be long and detailed.",
    ],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
)

audio_agent.print_response("Generate a very long audio of history of french revolution")
