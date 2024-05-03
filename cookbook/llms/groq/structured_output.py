from typing import List
from pydantic import BaseModel, Field
from rich.pretty import pprint
from phi.assistant import Assistant
from phi.llm.groq import Groq


class MovieScript(BaseModel):
    name: str = Field(..., description="Give a name to this movie")
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    genre: str = Field(..., description="Genre of the movie. If not available, select action or romantic comedy.")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


movie_assistant = Assistant(
    llm=Groq(model="mixtral-8x7b-32768"),
    description="You help people write movie scripts.",
    output_model=MovieScript,
)

pprint(movie_assistant.run("New York"))
# movie_assistant.cli_app(user="Theme", stream=False)
