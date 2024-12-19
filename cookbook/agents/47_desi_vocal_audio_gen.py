"""
pip install requests
"""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.desi_vocal_tools import DesiVocalTools

audio_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DesiVocalTools()],
    description="You are an AI agent that can generate audio using the DesiVocal API.",
    instructions=[
        "When the user asks you to generate audio, use the `text_to_speech` tool to generate the audio.",
        "You'll generate the appropriate prompt to send to the tool to generate audio.",
        "You don't need to find the appropriate voice first, I already specified the voice to user.",
        "Return the audio file name in your response. Don't convert it to markdown.",
        "Generate the text prompt we send in hindi language",
    ],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
)

audio_agent.print_response("Generate a very small audio of history of french revolution")
