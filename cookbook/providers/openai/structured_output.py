from typing import List
from rich.pretty import pprint  # noqa
from pydantic import BaseModel, Field
from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat


class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(
        ..., description="Genre of the movie. If not available, select action, thriller or romantic comedy."
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


# Agent with a response_model
movie_agent_1 = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You help people write movie scripts.",
    response_model=MovieScript,
)

# Agent with a response_model and structured_outputs
movie_agent_2 = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"),
    description="You help people write movie scripts.",
    response_model=MovieScript,
    structured_outputs=True,
)


# Get the response in a variable
run1: RunResponse = movie_agent_1.run("New York")
pprint(run1.content)
run2: RunResponse = movie_agent_2.run("New York")
pprint(run2.content)

movie_agent_1.print_response("New York")
movie_agent_2.print_response("New York")
