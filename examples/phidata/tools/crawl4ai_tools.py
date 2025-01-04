from phi.agent import Agent
from phi.tools.crawl4ai_tools import Crawl4aiTools

agent = Agent(tools=[Crawl4aiTools(max_length=None)], show_tool_calls=True)
agent.print_response("Tell me about https://github.com/phidatahq/phidata.")
