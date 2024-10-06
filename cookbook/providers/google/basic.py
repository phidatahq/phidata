from phi.agent import Agent, RunResponse  # noqa
from phi.model.google import Gemini

agent = Agent(model=Gemini(id="gemini-1.5-flash"), markdown=True, debug_mode=True)

# Get the response in a variable
# run: RunResponse = agent.run("Share a 2 sentence horror story")
# print(run.content)

# Print the response in the terminal
agent.print_response("Share a 2 sentence horror story")
