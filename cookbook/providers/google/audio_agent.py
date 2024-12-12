from phi.agent import Agent
from phi.model.google import Gemini
from google.generativeai import upload_file

agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    markdown=True,
)

# Please upload the audio file using
audio_file = upload_file("sample_audio.mp3")
print(f"Uploaded audio: {audio_file}")

# Please download a sample audio file to test this Agent
agent.print_response(
    "Tell me about this audio",
    audio=[audio_file],
    stream=True,
)
