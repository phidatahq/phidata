from phi.agent import Agent, RunResponse # noqa
from phi.model.together import Together

agent = Agent(
    model=Together(id="mistralai/Mixtral-8x7B-Instruct-v0.1"),
    description="You help people with their health and fitness goals.",
    markdown=True,
    show_tool_calls=True
)

# Get the response in a variable
# run: RunResponse = agent.run("Share a 2 sentence quick and healthy breakfast recipe.", stream=True)
# for chunk in run:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("Share a quick healthy breakfast recipe.", stream=True)
