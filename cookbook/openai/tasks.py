from phi.llm.openai import OpenAIChat
from phi.task.llm import LLMTask
from phi.assistant import Assistant
from pydantic import BaseModel, Field


class StoryTheme(BaseModel):
    setting: str = Field(
        ...,
        description="This is the context of the story. If not available, provide a random setting.",
    )
    genre: str = Field(..., description="This is the genre of the story. If not provided, select horror.")


get_story_theme = LLMTask(
    system_prompt="Generate a theme for a story.",
    output_model=StoryTheme,
    show_output=False,
)

write_story = LLMTask(
    llm=OpenAIChat(model="gpt-4"),
    system_prompt="Write a 2 sentence story for a given theme. It should be less than 30 words.",
)

give_story_a_name = LLMTask(
    system_prompt="Give this story a 2 word name. Format output as `Name: {name}`. Don't surround with quotes.",
)

story_generator = Assistant(tasks=[get_story_theme, write_story, give_story_a_name])
story_generator.cli_app(user="Theme", markdown=True)
