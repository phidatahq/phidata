import os

from phi.agent import Agent
from phi.tools.exa import ExaTools

os.environ["EXA_API_KEY"] = "your api key"

agent = Agent(tools=[ExaTools(include_domains=["cnbc.com", "reuters.com", "bloomberg.com"])], show_tool_calls=True)
agent.print_response("Search for AAPL news", debug_mode=True, markdown=True)
