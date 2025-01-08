from pathlib import Path

from phi.agent import Agent
from phi.model.google import Gemini
from google.generativeai import upload_file

agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
)

# Please download a sample audio file to test this Agent and upload using:
audio_path = Path(__file__).parent.joinpath("sample_audio.mp3")
audio_file = upload_file(audio_path)
print(f"Uploaded audio: {audio_file}")

agent.print_response(
    "Tell me about this audio",
    audio=audio_file,
    stream=True,
)
