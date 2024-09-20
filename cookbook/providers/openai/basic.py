from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    description="You help people with their health and fitness goals.",
)

run: RunResponse = agent.run("Share a healthy breakfast recipe")  # type: ignore

print(run.content)
