from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.utils.audio import write_audio_to_file

# Prompt the agent and get result as text + audio
agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
    markdown=True,
)
agent.print_response("Tell me a story")

# Save the response audio to a file
if agent.run_response.response_audio is not None:
    print("Transcript", agent.run_response.response_audio.transcript)
    write_audio_to_file(audio=agent.run_response.response_audio.base64_audio, filename="tmp/response.wav")
