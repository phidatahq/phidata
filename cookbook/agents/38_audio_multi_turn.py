import base64
from phi.agent import Agent
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
    add_history_to_messages=True,
)

agent.run("Is a golden retriever a good family dog?")
if agent.run_response.audio is not None and "data" in agent.run_response.audio:
    wav_bytes = base64.b64decode(agent.run_response.audio["data"])
    with open("tmp/answer_1.wav", "wb") as f:
        f.write(wav_bytes)

agent.run("Why do you say they are loyal?")
if agent.run_response.audio is not None and "data" in agent.run_response.audio:
    wav_bytes = base64.b64decode(agent.run_response.audio["data"])
    with open("tmp/answer_2.wav", "wb") as f:
        f.write(wav_bytes)
