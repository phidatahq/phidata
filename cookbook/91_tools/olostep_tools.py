"""
This is an example of how to use the OlostepTools.

Prerequisites:
- Create an Olostep account and get an API key: https://www.olostep.com/dashboard/api-keys
- Install the SDK:
    pip install olostep
- Set the API key as an environment variable:
    export OLOSTEP_API_KEY=<your-api-key>
"""

from agno.agent import Agent
from agno.tools.olostep import OlostepTools

# ---------------------------------------------------------------------------
# Create Agents
# ---------------------------------------------------------------------------

# Scrape a single page (scrape_url is on by default)
scrape_agent = Agent(
    tools=[OlostepTools()],
    markdown=True,
)

# Web search and AI answers grounded in live web data
research_agent = Agent(
    tools=[OlostepTools(scrape_url=False, search_web=True, answer_question=True)],
    markdown=True,
)

# Map a site, then scrape the pages that were found in one batch
batch_agent = Agent(
    tools=[OlostepTools(scrape_url=False, map_website=True, batch_scrape=True)],
    markdown=True,
)

# ---------------------------------------------------------------------------
# Run Agents
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Should use scrape_url
    scrape_agent.print_response(
        "Summarize the key features described at https://docs.olostep.com/get-started/welcome"
    )

    # Should use search_web and answer_question
    research_agent.print_response(
        "What are the top web scraping APIs and how do they compare on pricing?"
    )

    # Should use map_website, then batch_scrape
    batch_agent.print_response(
        "Map https://docs.olostep.com, pick the pages about features, "
        "then batch scrape them and summarize each feature."
    )
