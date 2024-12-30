from phi.agent import Agent
from phi.model.openai.chat import OpenAIChat
from phi.tools.firecrawl import FirecrawlTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[FirecrawlTools(scrape=True, crawl=True, async_crawl=True, map=True, limit=25)],
    show_tool_calls=True,
    markdown=True,
)


url = "https://docs.phidata.com/agents"

agent.print_response(f"scrape and summarize the following website: {url}")

agent.print_response(f"Crawl and analyze the main use cases and insights using asynchronous crawling: {url}")
