from phi.agent import Agent, RunResponse # noqa
from phi.model.anyscale import Anyscale

agent = Agent(
    model=Anyscale(id="mistralai/Mixtral-8x7B-Instruct-v0.1"),
    description="You help people with their health and fitness goals.",
    markdown=True,
    show_tool_calls=True
)

# Get the response in a variable
# run: RunResponse = agent.run("Share a 2 sentence quick and healthy breakfast recipe.", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("Share a 2 sentence quick and healthy breakfast recipe.", stream=True)
