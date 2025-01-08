from pathlib import Path

from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.utils.audio import write_audio_to_file

# Prompt the agent and get result as text + audio
agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
)
agent.print_response("Tell me a story")

filename = Path(__file__).parent.joinpath("tmp/response.wav")
filename.parent.mkdir(parents=True, exist_ok=True)

# Save the response audio to a file
if agent.run_response.response_audio is not None:
    write_audio_to_file(audio=agent.run_response.response_audio.base64_audio, filename=str(filename))
