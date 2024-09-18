from rich.pretty import pprint
from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    markdown=True,
    debug_mode=True,
)

run1: RunResponse = agent.run(
    "What’s in this image?",
    images=[
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
    ],
)  # type: ignore
pprint(run1.content)
