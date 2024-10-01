from phi.agent import Agent
from phi.model.together import Together

agent = Agent(
    model=Together(id="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"),
    description="You help people with their health and fitness goals.",
    markdown=True,
    show_tool_calls=True,
)

# Get the response in a variable
# run: RunResponse = agent.run("Share a 2 sentence quick and healthy breakfast recipe.")
# print(run.content)

# Print the response on the terminal
agent.print_response("Share a quick healthy breakfast recipe.")
