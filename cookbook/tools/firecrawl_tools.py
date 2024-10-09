# pip install firecrawl-py openai

import os

from phi.agent import Agent
from phi.tools.firecrawl import FirecrawlTools

api_key = os.getenv("FIRECRAWL_API_KEY")

agent = Agent(tools=[FirecrawlTools(api_key=api_key, scrape=False, crawl=True)], show_tool_calls=True, markdown=True)
agent.print_response("summarize this https://finance.yahoo.com/")
