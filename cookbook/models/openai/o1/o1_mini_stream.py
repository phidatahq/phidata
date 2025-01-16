from typing import Iterator  # noqa
from agno.agent import Agent, RunResponse  # noqa
from agno.models.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="o1-mini"))

# Print the response in the terminal
agent.print_response("What is the closest galaxy to milky way?", stream=True)
