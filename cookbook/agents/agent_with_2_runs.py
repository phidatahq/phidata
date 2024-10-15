from phi.agent import Agent
from phi.model.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="gpt-4o"), markdown=True)

agent.print_response("Share a 2 sentence horror story")
agent.print_response("Share a 5 sentence funny story")
