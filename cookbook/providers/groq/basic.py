from phi.agent import Agent, RunResponse  # noqa
from phi.model.groq import Groq

agent = Agent(model=Groq(id="llama3-groq-70b-8192-tool-use-preview"), instructions=["Respond in a southern tone"], markdown=True)

# Get the response in a variable
# run: RunResponse = agent.run("Explain simulation theory")
# print(run.content)

# Print the response on the terminal
agent.print_response("Explain simulation theory")
