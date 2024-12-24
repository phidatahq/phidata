import base64
import requests
from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.utils.audio import write_audio_to_file

# Fetch the audio file and convert it to a base64 encoded string
url = "https://openaiassets.blob.core.windows.net/$web/API/docs/audio/alloy.wav"
response = requests.get(url)
response.raise_for_status()
wav_data = response.content
encoded_string = base64.b64encode(wav_data).decode("utf-8")

# Provide the agent with the audio file and audio configuration and get result as text + audio
agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
    markdown=True,
)
agent.print_response("What is in this audio?", audio={"data": encoded_string, "format": "wav"})

# Save the response audio to a file
if agent.run_response.response_audio is not None and "data" in agent.run_response.response_audio:
    write_audio_to_file(audio=agent.run_response.response_audio["data"], filename="tmp/dog.wav")
