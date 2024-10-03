from phi.agent import Agent, RunResponse  # noqa
from phi.model.anyscale import Anyscale

agent = Agent(model=Anyscale(id="mistralai/Mixtral-8x7B-Instruct-v0.1"), markdown=True)

# Get the response in a variable
# run: RunResponse = agent.run("Share a 2 sentence horror story")
# print(run.content)

# Print the response in the terminal
agent.print_response("Share a 2 sentence horror story")
