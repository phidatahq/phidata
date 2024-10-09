from phi.agent import Agent
from phi.tools.spider import SpiderTools

agent = Agent(
    tools=[SpiderTools()],
    show_tool_calls=True,
    debug_mode=True,
)

agent.print_response('Can you scrape the first search result from a search on "news in USA"?', markdown=True)
