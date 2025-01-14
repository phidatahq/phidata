from pathlib import Path

from google.generativeai import upload_file
from agno.agent import Agent
from agno.models.google import Gemini

agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
)

# Please download a sample audio file to test this Agent and upload using:
audio_path = Path(__file__).parent.joinpath("sample_audio.mp3")
audio_file = upload_file(audio_path)
print(f"Using audio as input: {audio_file}")

agent.print_response(
    "Tell me about this audio",
    audio=audio_file,
    stream=True,
)
