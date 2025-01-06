from phi.agent import Agent
from phi.tools.apify import ApifyTools

agent = Agent(tools=[ApifyTools()], show_tool_calls=True)
agent.print_response("Tell me about https://docs.phidata.com/introduction", markdown=True)
