from typing import List
from pydantic import BaseModel, Field
from rich.pretty import pprint  # noqa

from phi.agent import Agent, RunResponse  # noqa
from phi.model.anyscale import Anyscale


class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(
        ..., description="Genre of the movie. If not available, select action, thriller or romantic comedy."
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


movie_writer = Agent(
    model=Anyscale(id="mistralai/Mixtral-8x7B-Instruct-v0.1"),
    description="You help people write movie scripts.",
    response_model=MovieScript,
    debug_mode=True,
)

# Get the response in a variable
# run: RunResponse = movie_writer.run("New York")
# pprint(run.content)

movie_writer.print_response("New York")