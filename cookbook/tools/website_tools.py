from phi.agent import Agent
from phi.tools.website import WebsiteTools

agent = Agent(tools=[WebsiteTools()], show_tool_calls=True)
agent.print_response("Search web page: 'https://docs.phidata.com/introduction'", markdown=True)
