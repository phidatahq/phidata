from typing import Iterator
from rich.pretty import pprint
from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAI
from agno.tools.dalle import DalleTools

image_agent = Agent(
    model=OpenAI(id="gpt-4o"),
    tools=[DalleTools()],
    description="You are an AI agent that can create images using DALL-E.",
    instructions=[
        "When the user asks you to create an image, use the DALL-E tool to create an image.",
        "The DALL-E tool will return an image URL.",
        "Return the image URL in your response in the following format: `![image description](image URL)`",
    ],
    markdown=True,
)

run_stream: Iterator[RunResponse] = image_agent.run(
    "Create an image of a yellow siamese cat",
    stream=True,
    stream_intermediate_steps=True,
)
for chunk in run_stream:
    pprint(chunk.model_dump(exclude={"messages"}))
    print("---" * 20)
