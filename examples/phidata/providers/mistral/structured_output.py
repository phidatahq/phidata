import os

from typing import List
from rich.pretty import pprint  # noqa
from pydantic import BaseModel, Field
from phi.agent import Agent, RunResponse  # noqa
from phi.model.mistral import MistralChat

mistral_api_key = os.getenv("MISTRAL_API_KEY")


class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(
        ..., description="Genre of the movie. If not available, select action, thriller or romantic comedy."
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


json_mode_agent = Agent(
    model=MistralChat(
        id="mistral-large-latest",
        api_key=mistral_api_key,
    ),
    description="You help people write movie scripts.",
    response_model=MovieScript,
    # debug_mode=True,
)

# Get the response in a variable
# json_mode_response: RunResponse = json_mode_agent.run("New York")
# pprint(json_mode_response.content)

json_mode_agent.print_response("New York")
