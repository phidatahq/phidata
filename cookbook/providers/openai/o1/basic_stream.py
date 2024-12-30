from typing import Iterator  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="o1-preview"))

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("What is the closest galaxy to milky way?", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response in the terminal
agent.print_response("What is the closest galaxy to milky way?", stream=True)
