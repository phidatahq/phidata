from typing import List
from pydantic import BaseModel, Field
from rich.pretty import pprint
from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat


# Define the pydantic model you want the LLM to generate
class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    genre: str = Field(..., description="Genre of the movie. If not available, select action comedy.")
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="2 sentence storyline for the movie. Make it punchy!")


# Generate a list of pydantic models
class MovieScripts(BaseModel):
    movie_scripts: List[MovieScript] = Field(
        ..., description="List of movie scripts for the given theme. Provide 3 different scripts."
    )


# Define the Assistant
movie_assistant = Assistant(
    llm=OpenAIChat(model="gpt-4-turbo"),
    description="You help people write movie ideas. For every theme, provide 3 different scripts",
    output_model=MovieScripts,
)

# Run the assistant
pprint(movie_assistant.run("New York"))
