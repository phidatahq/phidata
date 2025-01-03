from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.utils.audio import write_audio_to_file

agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
    debug_mode=True,
    add_history_to_messages=True,
)

agent.run("Is a golden retriever a good family dog?")
if agent.run_response.response_audio is not None and "data" in agent.run_response.response_audio:
    write_audio_to_file(audio=agent.run_response.response_audio["data"], filename="tmp/answer_1.wav")

agent.run("Why do you say they are loyal?")
if agent.run_response.response_audio is not None and "data" in agent.run_response.response_audio:
    write_audio_to_file(audio=agent.run_response.response_audio["data"], filename="tmp/answer_2.wav")
