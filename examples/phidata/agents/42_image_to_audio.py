from pathlib import Path
from rich import print
from rich.text import Text

from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.utils.audio import write_audio_to_file

cwd = Path(__file__).parent.resolve()

image_agent = Agent(model=OpenAIChat(id="gpt-4o"))
image_story: RunResponse = image_agent.run(
    "Write a 3 sentence fiction story about the image",
    images=[str(cwd.joinpath("multimodal-agents.jpg"))],
)
formatted_text = Text.from_markup(f":sparkles: [bold magenta]Story:[/bold magenta] {image_story.content} :sparkles:")
print(formatted_text)

audio_agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-audio-preview", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"}
    ),
)

audio_story: RunResponse = audio_agent.run(f"Narrate the story with flair: {image_story.content}")
if audio_story.response_audio is not None and "data" in audio_story.response_audio:
    write_audio_to_file(audio=audio_story.response_audio["data"], filename="tmp/multimodal-agents.wav")
