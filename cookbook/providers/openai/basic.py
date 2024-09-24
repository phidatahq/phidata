from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    instructions=["Respond in a southern tone"],
    # debug_mode=True,
)


# Return the result as a string
run: RunResponse = agent.run("Explain simulation theory")  # type: ignore

print(run.content)
