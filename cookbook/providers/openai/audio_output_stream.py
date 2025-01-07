import base64
from typing import Iterator

from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat

# Provide the agent with the audio file and audio configuration and get result as text + audio
agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
    markdown=True,
)
output_stream: Iterator[RunResponse] = agent.run("Tell me a story", stream=True)

filename="tmp/dog.wav"

# Open the file once in append-binary mode
with open(filename, "ab") as f:
    # Iterate over generated audio
    for response in output_stream:
        print(response.content)
        if hasattr(response, 'response_audio') and response.response_audio:
            try:
                wav_bytes = base64.b64decode(response.response_audio)
                f.write(wav_bytes)
            except base64.binascii.Error as e:
                print(f"Error decoding audio: {e}")
        else:
            print("No audio found in the response.")
