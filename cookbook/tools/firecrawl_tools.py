from phi.agent import Agent
from phi.tools.firecrawl import FirecrawlTools


def agent_with_predefined_toolkit(url: str):
    agent = Agent(
        tools=[FirecrawlTools(map=True, scrape=True)],
        show_tool_calls=True,
        markdown=True,
        reasoning=True,
    )
    agent.print_response(f"Fetch all the blog links from the website: {url}")
    agent.print_response(
        "scrape and summarize the following website: https://www.firecrawl.dev/blog/using-structured-output-and-json-strict-mode-openai"
    )


def crawl_example(url: str):
    agent = Agent(
        tools=[FirecrawlTools(scrape=True, crawl=True, async_crawl=True, limit=25)],
        show_tool_calls=True,
        reasoning=True,
        markdown=True,
    )
    agent.print_response(f"Crawl and analyze the main use cases and  insights using asynchronous crawling: {url}")


if __name__ == "__main__":
    url = "https://www.firecrawl.dev/blog"
    agent_with_predefined_toolkit(url)
    crawl_example(url)
