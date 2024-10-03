from typing import Iterator  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.groq import Groq

agent = Agent(model=Groq(id="llama3-groq-70b-8192-tool-use-preview"), markdown=True)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("Share a 2 sentence horror story", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("Share a 2 sentence horror story", stream=True)
