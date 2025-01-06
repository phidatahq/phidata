from phi.agent import Agent
from phi.tools.firecrawl import FirecrawlTools

agent = Agent(tools=[FirecrawlTools(scrape=False, crawl=True)], show_tool_calls=True, markdown=True)
agent.print_response("Summarize this https://finance.yahoo.com/")
