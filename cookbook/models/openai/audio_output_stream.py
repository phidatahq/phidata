import base64
import wave
from pathlib import Path
from typing import Iterator

from agno.agent import Agent, RunResponse  # noqa
from agno.models.openai import OpenAIChat

# Audio Configuration
SAMPLE_RATE = 24000  # Hz (24kHz)
CHANNELS = 1  # Mono (Change to 2 if Stereo)
SAMPLE_WIDTH = 2  # Bytes (16 bits)

# Provide the agent with the audio file and audio configuration and get result as text + audio
agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={
            "voice": "alloy",
            "format": "pcm16",
        },  # Only pcm16 is supported with streaming
    ),
)
output_stream: Iterator[RunResponse] = agent.run(
    "Tell me a 10 second story", stream=True
)

filename = Path(__file__).parent.joinpath("tmp/response_stream.wav")
filename.unlink(missing_ok=True)
filename.parent.mkdir(parents=True, exist_ok=True)

# Open the file once in append-binary mode
with wave.open(str(filename), "wb") as wav_file:
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(SAMPLE_WIDTH)
    wav_file.setframerate(SAMPLE_RATE)

    # Iterate over generated audio
    for response in output_stream:
        if response.response_audio:
            print(response.response_audio.transcript, end="", flush=True)
            if hasattr(response, "response_audio") and response.response_audio:
                try:
                    pcm_bytes = base64.b64decode(response.response_audio.base64_audio)
                    wav_file.writeframes(pcm_bytes)
                except Exception as e:
                    print(f"Error decoding audio: {e}")
            else:
                print("No audio found in the response.")
print()
