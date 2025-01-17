"""🔍 News Research Workflow - Your AI News Assistant!
Run `pip install openai duckduckgo-search newspaper4k lxml_html_clean sqlalchemy agno` to install dependencies.

This tutorial demonstrates how to build a sophisticated news research workflow that:
🤖 Searches the web for relevant articles
📰 Scrapes and processes article content
✍️ Generates engaging NYT-style reports
💾 Implements smart caching for efficiency
"""

import json
from textwrap import dedent
from typing import Dict, Iterator, Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.workflow.sqlite import SqlWorkflowStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.utils.log import logger
from agno.utils.pprint import pprint_run_response
from agno.workflow import RunEvent, RunResponse, Workflow
from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(
        ..., description="Summary of the article if available."
    )


class SearchResults(BaseModel):
    articles: list[NewsArticle]


class ScrapedArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(
        ..., description="Summary of the article if available."
    )
    content: Optional[str] = Field(
        ...,
        description="Content of the in markdown format if available. Return None if the content is not available or does not make sense.",
    )


class NewsReportGenerator(Workflow):
    description: str = """🗞️ Generate comprehensive, engaging news reports that combine
    the journalistic excellence of NYT with the analytical depth of a research paper."""

    web_searcher: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[DuckDuckGoTools()],
        instructions=[
            "You're a seasoned investigative journalist with a nose for compelling stories! 🔍",
            "Search for 10 articles and identify the 5 most relevant and credible sources.",
            "Look for diverse perspectives and authoritative sources.",
            "Prioritize recent articles from reputable news outlets.",
        ],
        response_model=SearchResults,
    )

    article_scraper: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[Newspaper4kTools()],
        instructions=[
            "You're a master content curator with an eye for quality! 📚",
            "Extract and format article content while preserving key information.",
            "Clean and structure the content for optimal readability.",
            "If content is paywalled or unavailable, return None gracefully.",
        ],
        response_model=ScrapedArticle,
    )

    writer: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="You are a Pulitzer-worthy Senior NYT Editor crafting compelling narratives that inform and inspire! ✨",
        instructions=[
            "Channel the storytelling prowess of the New York Times' finest editors!",
            "🎯 First, thoroughly analyze each source article",
            "💡 Then, identify the most compelling narrative threads",
            "✍️ Finally, weave a masterful story that:",
            "  - Hooks readers from the first paragraph",
            "  - Presents complex information clearly",
            "  - Balances depth with accessibility",
            "  - Includes diverse perspectives",
            "  - Backs every claim with solid sources",
            "Remember: You're writing for the front page of the NYT - make every word count!",
        ],
        expected_output=dedent("""\
        ## 🗞️ [Engaging Headline That Captures Attention]

        ### 🎯 The Big Picture
        {compelling introduction that sets the context}
        {why this story matters right now}

        ### 💡 Key Developments
        {main story elements with supporting evidence}
        {expert insights and analysis}

        ### 🌟 Impact & Implications
        {real-world significance}
        {future implications}

        ### 📊 Key Takeaways
        - {critical point 1}
        - {critical point 2}
        - {critical point 3}

        ### 📚 Sources
        - [Source 1](url)
        - [Source 2](url)
        - [Source 3](url)

        _Generated by NewsReportGenerator - Bringing you tomorrow's news, today! ✨_
        """),
    )

    def run(
        self,
        topic: str,
        use_search_cache: bool = True,
        use_scrape_cache: bool = True,
        use_cached_report: bool = True,
    ) -> Iterator[RunResponse]:
        """
        Generate a comprehensive news report on a given topic.

        This function orchestrates a workflow to search for articles, scrape their content,
        and generate a final report. It utilizes caching mechanisms to optimize performance.

        Args:
            topic (str): The topic for which to generate the news report.
            use_search_cache (bool, optional): Whether to use cached search results. Defaults to True.
            use_scrape_cache (bool, optional): Whether to use cached scraped articles. Defaults to True.
            use_cached_report (bool, optional): Whether to return a previously generated report on the same topic. Defaults to False.

        Returns:
            Iterator[RunResponse]: An stream of objects containing the generated report or status information.

        Steps:
        1. Check for a cached report if use_cached_report is True.
        2. Search the web for articles on the topic:
            - Use cached search results if available and use_search_cache is True.
            - Otherwise, perform a new web search.
        3. Scrape the content of each article:
            - Use cached scraped articles if available and use_scrape_cache is True.
            - Scrape new articles that aren't in the cache.
        4. Generate the final report using the scraped article contents.

        The function utilizes the `session_state` to store and retrieve cached data.
        """
        logger.info(f"Generating a report on: {topic}")

        # Use the cached report if use_cached_report is True
        if use_cached_report:
            cached_report = self.get_report_from_cache(topic)
            if cached_report:
                yield RunResponse(
                    content=cached_report, event=RunEvent.workflow_completed
                )
                return

        # Search the web for articles on the topic
        search_results: Optional[SearchResults] = self.get_search_results(
            topic, use_search_cache
        )
        # If no search_results are found for the topic, end the workflow
        if search_results is None or len(search_results.articles) == 0:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find any articles on the topic: {topic}",
            )
            return

        # Scrape the search results
        scraped_articles: Dict[str, ScrapedArticle] = self.scrape_articles(
            search_results, use_scrape_cache
        )

        # Write a news report
        yield from self.write_news_report(topic, scraped_articles)

    def get_report_from_cache(self, topic: str) -> Optional[str]:
        logger.info("Checking if cached report exists")
        return self.session_state.get("reports", {}).get(topic)

    def add_report_to_cache(self, topic: str, report: Optional[str]):
        logger.info(f"Saving report for topic: {topic}")
        self.session_state.setdefault("reports", {})
        self.session_state["reports"][topic] = report

    def get_search_results(
        self, topic: str, use_search_cache: bool
    ) -> Optional[SearchResults]:
        search_results: Optional[SearchResults] = None

        # Get cached search_results from the session state if use_search_cache is True
        if (
            use_search_cache
            and "search_results" in self.session_state
            and topic in self.session_state["search_results"]
        ):
            try:
                search_results = SearchResults.model_validate(
                    self.session_state["search_results"][topic]
                )
                logger.info(f"Found {len(search_results.articles)} articles in cache.")
            except Exception as e:
                logger.warning(f"Could not read search results from cache: {e}")

        # If there are no cached search_results, ask the web_searcher to find the latest articles
        if search_results is None:
            web_searcher_response: RunResponse = self.web_searcher.run(topic)
            if (
                web_searcher_response
                and web_searcher_response.content
                and isinstance(web_searcher_response.content, SearchResults)
            ):
                logger.info(
                    f"WebSearcher identified {len(web_searcher_response.content.articles)} articles."
                )
                search_results = web_searcher_response.content

        if search_results is not None:
            # Initialize search_results dict if it doesn't exist
            if "search_results" not in self.session_state:
                self.session_state["search_results"] = {}
            # Cache the search results
            self.session_state["search_results"][topic] = search_results.model_dump()

        return search_results

    def scrape_articles(
        self, search_results: SearchResults, use_scrape_cache: bool
    ) -> Dict[str, ScrapedArticle]:
        scraped_articles: Dict[str, ScrapedArticle] = {}

        # Get cached scraped_articles from the session state if use_scrape_cache is True
        if (
            use_scrape_cache
            and "scraped_articles" in self.session_state
            and isinstance(self.session_state["scraped_articles"], dict)
        ):
            for url, scraped_article in self.session_state["scraped_articles"].items():
                try:
                    validated_scraped_article = ScrapedArticle.model_validate(
                        scraped_article
                    )
                    scraped_articles[validated_scraped_article.url] = (
                        validated_scraped_article
                    )
                except Exception as e:
                    logger.warning(f"Could not read scraped article from cache: {e}")
            logger.info(f"Found {len(scraped_articles)} scraped articles in cache.")

        # Scrape the articles that are not in the cache
        for article in search_results.articles:
            if article.url in scraped_articles:
                logger.info(f"Found scraped article in cache: {article.url}")
                continue

            article_scraper_response: RunResponse = self.article_scraper.run(
                article.url
            )
            if (
                article_scraper_response
                and article_scraper_response.content
                and isinstance(article_scraper_response.content, ScrapedArticle)
            ):
                scraped_articles[article_scraper_response.content.url] = (
                    article_scraper_response.content
                )
                logger.info(f"Scraped article: {article_scraper_response.content.url}")

        # Save the scraped articles in the session state
        if "scraped_articles" not in self.session_state:
            self.session_state["scraped_articles"] = {}
        for url, scraped_article in scraped_articles.items():
            self.session_state["scraped_articles"][url] = scraped_article.model_dump()

        return scraped_articles

    def write_news_report(
        self, topic: str, scraped_articles: Dict[str, ScrapedArticle]
    ) -> Iterator[RunResponse]:
        logger.info("Writing news report")
        # Prepare the input for the writer
        writer_input = {
            "topic": topic,
            "articles": [v.model_dump() for v in scraped_articles.values()],
        }
        # Run the writer and yield the response
        yield from self.writer.run(json.dumps(writer_input, indent=4), stream=True)
        # Save the blog post in the cache
        self.add_report_to_cache(topic, self.writer.run_response.content)


# Run the workflow if the script is executed directly
if __name__ == "__main__":
    from rich.prompt import Prompt

    # Get topic from user
    topic = Prompt.ask(
        "[bold]Enter a news report topic[/bold]\n✨",
        default="Agentic Systems",
    )

    # Convert the topic to a URL-safe string for use in session_id
    url_safe_topic = topic.lower().replace(" ", "-")

    # Initialize the news report generator workflow
    generate_news_report = NewsReportGenerator(
        session_id=f"generate-report-on-{url_safe_topic}",
        storage=SqlWorkflowStorage(
            table_name="generate_news_report_workflows",
            db_file="tmp/workflows.db",
        ),
    )

    # Execute the workflow with caching enabled
    report_stream: Iterator[RunResponse] = generate_news_report.run(
        topic=topic,
        use_search_cache=True,
        use_scrape_cache=True,
        use_cached_report=True,
    )

    # Print the response
    pprint_run_response(report_stream, markdown=True)