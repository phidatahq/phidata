"""Please install dependencies using:
pip install openai duckduckgo-search newspaper4k lxml_html_clean phidata
"""

import json
from textwrap import dedent
from typing import Optional, Dict

from pydantic import BaseModel, Field

from phi.agent import Agent
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")


class SearchResults(BaseModel):
    articles: list[NewsArticle]


class ScrapedArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")
    content: Optional[str] = Field(
        ...,
        description="Content of the in markdown format if available. Return None if the content is not available or does not make sense.",
    )


class GenerateNewsReport(Workflow):
    web_searcher: Agent = Agent(
        tools=[DuckDuckGo()],
        instructions=[
            "Given a topic, search for 10 articles and return the 5 most relevant articles.",
        ],
        response_model=SearchResults,
    )

    article_scraper: Agent = Agent(
        tools=[Newspaper4k()],
        instructions=[
            "Given a url, scrape the article and return the title, url, and markdown formatted content.",
            "If the content is not available or does not make sense, return None as the content.",
        ],
        response_model=ScrapedArticle,
    )

    writer: Agent = Agent(
        description="You are a Senior NYT Editor and your task is to write a new york times worthy cover story.",
        instructions=[
            "You will be provided with news articles and their contents.",
            "Carefully **read** each article and **think** about the contents",
            "Then generate a final New York Times worthy article in the <article_format> provided below.",
            "Break the article into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Always provide sources for the article, do not make up information or sources.",
            "REMEMBER: you are writing for the New York Times, so the quality of the article is important.",
        ],
        expected_output=dedent("""\
        An engaging, informative, and well-structured article in the following format:
        <article_format>
        ## Engaging Article Title

        ### {Overview or Introduction}
        {give a brief introduction of the article and why the user should read this report}
        {make this section engaging and create a hook for the reader}

        ### {Section title}
        {break the article into sections}
        {provide details/facts/processes in this section}

        ... more sections as necessary...

        ### Key Takeaways
        {provide key takeaways from the article}

        ### Sources
        - [Title](url)
        - [Title](url)
        - [Title](url)
        </article_format>
        """),
    )

    def run(
        self, topic: str, use_search_cache: bool = True, use_scrape_cache: bool = True, use_cached_report: bool = False
    ) -> RunResponse:
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
            RunResponse: An object containing the generated report or status information.

        Workflow Steps:
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
        if use_cached_report and "reports" in self.session_state:
            logger.info("Checking if cached report exists")
            for cached_report in self.session_state["reports"]:
                if cached_report["topic"] == topic:
                    return RunResponse(
                        run_id=self.run_id,
                        event=RunEvent.workflow_completed,
                        content=cached_report["report"],
                    )

        ####################################################
        # Step 1: Search the web for articles on the topic
        ####################################################

        # 1.1: Get cached search_results from the session state if use_search_cache is True
        search_results: Optional[SearchResults] = None
        try:
            if use_search_cache and "search_results" in self.session_state:
                search_results = SearchResults.model_validate(self.session_state["search_results"])
                logger.info(f"Found {len(search_results.articles)} articles in cache.")
        except Exception as e:
            logger.warning(f"Could not read search results from cache: {e}")

        # 1.2: If there are no cached search_results, ask the web_searcher to find the latest articles
        if search_results is None:
            web_searcher_response: RunResponse = self.web_searcher.run(topic)
            if (
                web_searcher_response
                and web_searcher_response.content
                and isinstance(web_searcher_response.content, SearchResults)
            ):
                logger.info(f"WebSearcher identified {len(web_searcher_response.content.articles)} articles.")
                search_results = web_searcher_response.content
                # Save the search_results in the session state
                self.session_state["search_results"] = search_results.model_dump()

        # 1.3: If no search_results are found for the topic, end the workflow
        if search_results is None or len(search_results.articles) == 0:
            return RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find any articles on the topic: {topic}",
            )

        ####################################################
        # Step 2: Scrape each article
        ####################################################

        # 2.1: Get cached scraped_articles from the session state if use_scrape_cache is True
        scraped_articles: Dict[str, ScrapedArticle] = {}
        if (
            use_scrape_cache
            and "scraped_articles" in self.session_state
            and isinstance(self.session_state["scraped_articles"], dict)
        ):
            for url, scraped_article in self.session_state["scraped_articles"].items():
                try:
                    validated_scraped_article = ScrapedArticle.model_validate(scraped_article)
                    scraped_articles[validated_scraped_article.url] = validated_scraped_article
                except Exception as e:
                    logger.warning(f"Could not read scraped article from cache: {e}")
            logger.info(f"Found {len(scraped_articles)} scraped articles in cache.")

        # 2.2: Scrape the articles that are not in the cache
        for article in search_results.articles:
            if article.url in scraped_articles:
                logger.info(f"Found scraped article in cache: {article.url}")
                continue

            article_scraper_response: RunResponse = self.article_scraper.run(article.url)
            if (
                article_scraper_response
                and article_scraper_response.content
                and isinstance(article_scraper_response.content, ScrapedArticle)
            ):
                scraped_articles[article_scraper_response.content.url] = article_scraper_response.content
                logger.info(f"Scraped article: {article_scraper_response.content.url}")

        # 2.3: Save the scraped_articles in the session state
        self.session_state["scraped_articles"] = {k: v.model_dump() for k, v in scraped_articles.items()}

        ####################################################
        # Step 3: Write a report
        ####################################################

        # 3.1: Generate the final report
        logger.info("Generating final report")
        writer_input = {
            "topic": topic,
            "articles": [v.model_dump() for v in scraped_articles.values()],
        }
        writer_response: RunResponse = self.writer.run(json.dumps(writer_input, indent=4))

        # 3.2: Save the writer_response in the session state
        if writer_response.content is not None:
            if "reports" not in self.session_state:
                self.session_state["reports"] = []
            self.session_state["reports"].append({"topic": topic, "report": writer_response.content})

        return writer_response


# The topic to generate a report on
topic = "IBM Hashicorp Acquisition"

# Instantiate the workflow
generate_news_report = GenerateNewsReport(
    session_id=f"generate-report-on-{topic}",
    storage=SqlWorkflowStorage(
        table_name="generate_news_report_workflows",
        db_file="tmp/workflows.db",
    ),
)

# Run workflow
report: RunResponse = generate_news_report.run(
    topic=topic, use_search_cache=True, use_scrape_cache=True, use_cached_report=False
)

# Print the response
pprint_run_response(report, markdown=True)
