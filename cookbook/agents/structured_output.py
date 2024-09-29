import asyncio
from typing import List
from pydantic import BaseModel, Field
from rich.pretty import pprint
from phi.agent import Agent, AgentResponse
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


movie_agent_1 = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="You help people write movie scripts.",
    response_model=MovieScript,
)
print("Running Agent with response_model=MovieScript")
run_movie_agent_1: AgentResponse = movie_agent_1.run("New York")
pprint(run_movie_agent_1.content)

movie_agent_2 = Agent(
    model=OpenAIChat(id="gpt-4o-2024-08-06"),
    description="You help people write movie scripts.",
    response_model=MovieScript,
    structured_outputs=True,
)

print("Running Agent with response_model=MovieScript and structured_outputs=True")
run_movie_agent_2: AgentResponse = movie_agent_2.run("New York")
pprint(run_movie_agent_2.content)


async def main():
    print("Running Agent with response_model=MovieScript (async)")
    async_run_movie_agent_1: AgentResponse = await movie_agent_1.arun("New York")
    pprint(async_run_movie_agent_1.content)

    print("Running Agent with response_model=MovieScript and structured_outputs=True (async)")
    async_run_movie_agent_2: AgentResponse = await movie_agent_2.arun("New York")
    pprint(async_run_movie_agent_2.content)


asyncio.run(main())
