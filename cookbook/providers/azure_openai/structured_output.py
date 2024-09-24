import os
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from phi.agent import Agent, RunResponse
from phi.model.azure import AzureOpenAIChat

load_dotenv()


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


azure_model = AzureOpenAIChat(
    model=os.getenv("AZURE_OPENAI_MODEL_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
)

movie_agent = Agent(
    model=AzureOpenAIChat(model="gpt-4o"),
    description="You help people write movie scripts.",
    output_model=MovieScript,
)

run: RunResponse = movie_agent.run("New York")

print(run.content)
