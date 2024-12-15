import base64
import requests
from phi.agent import Agent
from phi.model.openai import OpenAIChat

# Fetch the audio file and convert it to a base64 encoded string
url = "https://openaiassets.blob.core.windows.net/$web/API/docs/audio/alloy.wav"
response = requests.get(url)
response.raise_for_status()
wav_data = response.content
encoded_string = base64.b64encode(wav_data).decode("utf-8")

agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
    markdown=True,
)

agent.run(
    "What's in these recording?",
    audio={"data": encoded_string, "format": "wav"},
)

if agent.run_response.audio is not None and "data" in agent.run_response.audio:
    wav_bytes = base64.b64decode(agent.run_response.audio["data"])
    with open("dog.wav", "wb") as f:
        f.write(wav_bytes)
