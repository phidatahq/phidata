from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="gpt-4o"), instructions="Speak with a southern drawl", markdown=True)

agent.print_response("Share a 1 sentence horror story", stream=True)
