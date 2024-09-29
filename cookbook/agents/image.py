from rich.pretty import pprint  # noqa
from phi.agent import Agent, AgentResponse
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    markdown=True,
    debug_mode=True,
)

# run: AgentResponse = agent.run(
#     "What’s in this image?",
#     images=[
#         "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
#     ],
# )  # type: ignore
# run: AgentResponse = agent.run(
#     "What’s in this image?",
#     images=[
#         {
#             "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
#             "detail": "high",
#         }
#     ],
# )  # type: ignore
run: AgentResponse = agent.run(
    "What are in these images? Is there any difference between them?",
    images=[
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
    ],
)  # type: ignore
print(run.content)
# pprint(run)
