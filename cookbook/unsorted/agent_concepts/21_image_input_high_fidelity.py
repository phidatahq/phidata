from agno.agent import Agent
from agno.models.openai import OpenAI

agent = Agent(
    model=OpenAI(id="gpt-4o"),
    markdown=True,
)

agent.print_response(
    "What's in these images",
    images=[
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
            "detail": "high",
        }
    ],
)
