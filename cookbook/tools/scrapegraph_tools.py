import os

from phi.agent import Agent
from phi.tools.scrapegraph_tools import ScrapeGraphTools

api_key = os.getenv("SGAI_API_KEY")

# Example 1: Default behavior - only smartscraper enabled
scrapegraph = ScrapeGraphTools(
    api_key=api_key,  # smartscraper=True by default
)

agent = Agent(tools=[scrapegraph], show_tool_calls=True, markdown=True)

# Use smartscraper
agent.print_response("""
Use smartscraper to extract the following from https://www.wired.com/category/science/:
- News articles
- Headlines
- Images
- Links
- Author
""")

# Example 2: Only markdownify enabled (by setting smartscraper=False)
scrapegraph_md = ScrapeGraphTools(
    api_key=api_key,
    smartscraper=False,  # This will automatically enable markdownify
)

agent_md = Agent(tools=[scrapegraph_md], show_tool_calls=True, markdown=True)

# Use markdownify
agent_md.print_response("Fetch and convert https://www.wired.com/category/science/ to markdown format")
