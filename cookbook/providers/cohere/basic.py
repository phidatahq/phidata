from phi.agent import Agent, RunResponse  # noqa
from phi.model.cohere import CohereChat

agent = Agent(model=CohereChat(id="command-r-plus"), instructions=["Respond in a southern tone"], markdown=True)

# Get the response in a variable
# run: RunResponse = agent.run("Explain simulation theory")
# print(run.content)

# Print the response on the terminal
agent.print_response("Explain simulation theory")
