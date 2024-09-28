from typing import Iterator  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.cohere import CohereChat

agent = Agent(model=CohereChat(id="command-r-plus"), instructions=["Respond in a southern tone"], markdown=True)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("Explain simulation theory", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("Explain simulation theory", stream=True)
