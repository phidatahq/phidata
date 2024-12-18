from phi.agent import Agent
from phi.tools.firecrawl import FirecrawlTools

agent = Agent(
    tools=[FirecrawlTools(scrape=True, crawl=True, async_crawl=True, map=True, limit=25)],
    show_tool_calls=True,
    reasoning=True,
    markdown=True,
)


def map_website_example(url: str):
    agent.print_response(f"Fetch all the blog links from the website: {url}")


def scrape_example(url: str):
    agent.print_response(f"scrape and summarize the following website: {url}")


def crawl_example(url: str):
    agent.print_response(f"Crawl and analyze the main use cases and insights using asynchronous crawling: {url}")


def async_crawl_example(url: str):
    agent.print_response(f"Crawl and analyze the main use cases and insights using asynchronous crawling: {url}")


if __name__ == "__main__":
    url = "https://docs.phidata.com/agents"
    map_website_example(url)
    crawl_example(url)
    async_crawl_example(url)
    scrape_url = "https://docs.phidata.com/workflows"
    scrape_example(scrape_url)
