from typing import Iterator  # noqa
from phi.agent import Agent, AgentResponse  # noqa
from phi.model.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="gpt-4o"), instructions=["Respond in a southern tone"], markdown=True)

# Get the response in a variable
# run_response: Iterator[AgentResponse] = agent.run("Explain simulation theory", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("Explain simulation theory", stream=True)
