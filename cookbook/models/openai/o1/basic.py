from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="o1-preview"))

# Get the response in a variable
# run: RunResponse = agent.run("What is the closest galaxy to milky way?")
# print(run.content)

# Print the response in the terminal
agent.print_response("What is the closest galaxy to milky way?")
