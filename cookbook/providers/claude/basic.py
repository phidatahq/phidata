from phi.agent import Agent, RunResponse  # noqa
from phi.model.anthropic import Claude

agent = Agent(
    model=Claude(id="claude-3-5-sonnet-20240620"),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)

# Get the response in a variable
# run: RunResponse = agent.run("Explain simulation theory")
# print(run.content)

# Print the response in the terminal
agent.print_response("Share a quick healthy breakfast recipe.", markdown=True)
