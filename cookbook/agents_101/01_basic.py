from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="gpt-4o"), instructions="Speak like a Shakespearean bard", markdown=True)

agent.print_response("Share a 2 sentence story", stream=True)
