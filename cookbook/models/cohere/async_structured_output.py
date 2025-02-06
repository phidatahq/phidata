import asyncio
from typing import List

from agno.agent import Agent, RunResponse  # noqa
from agno.models.cohere import Cohere
from agno.tools.duckduckgo import DuckDuckGoTools
from pydantic import BaseModel, Field
from rich.pretty import pprint  # noqa


class MovieScript(BaseModel):
    setting: str = Field(
        ..., description="Provide a nice setting for a blockbuster movie."
    )
    ending: str = Field(
        ...,
        description="Ending of the movie. If not available, provide a happy ending.",
    )
    genre: str = Field(
        ...,
        description="Genre of the movie. If not available, select action, thriller or romantic comedy.",
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(
        ..., description="3 sentence storyline for the movie. Make it exciting!"
    )


agent = Agent(
    model=Cohere(
        id="command-r-08-2024",
    ),
    tools=[DuckDuckGoTools()],
    description="You help people write movie scripts.",
    response_model=MovieScript,
    show_tool_calls=True,
    debug_mode=True,
)

# Get the response in a variable
# json_mode_response: RunResponse = await json_mode_agent.arun("New York")
# pprint(json_mode_response.content)

asyncio.run(agent.aprint_response("Find a cool movie idea about London and write it."))
