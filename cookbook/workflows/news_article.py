"""Please install dependencies using:
pip install openai duckduckgo-search newspaper4k lxml_html_clean phidata
"""

import json
from textwrap import dedent
from typing import Optional, Dict

from pydantic import BaseModel, Field

from phi.agent import Agent, RunResponse
from phi.workflow import Workflow
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")


class NewsArticles(BaseModel):
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
    researcher: Agent = Agent(
        tools=[DuckDuckGo()],
        instructions=[
            "Given a topic, search for 10 articles and return the 5 most relevant articles.",
        ],
        response_model=NewsArticles,
    )

    scraper: Agent = Agent(
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

        ### Overview
        {give a brief introduction of the article and why the user should read this report}
        {make this section engaging and create a hook for the reader}

        ### Section 1
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

    def run(self, topic: str, use_cache: bool = True) -> RunResponse:
        logger.info(f"Writing a report on: {topic}")

        # Add the topic to the session state
        self.session_state["topic"] = topic

        # Get the cached articles from the session state
        articles: Optional[NewsArticles] = None
        try:
            if use_cache and "articles" in self.session_state:
                articles = NewsArticles.model_validate(self.session_state["articles"])
                logger.info(f"Found {len(articles.articles)} articles in session state.")
        except Exception as e:
            logger.warning(f"Could not read articles from session state: {e}")

        # If no cached articles are available, ask the researcher to find the latest articles
        if articles is None:
            researcher_response: RunResponse = self.researcher.run(topic)
            if (
                researcher_response
                and researcher_response.content
                and isinstance(researcher_response.content, NewsArticles)
            ):
                logger.info(f"Researcher identified {len(researcher_response.content.articles)} articles.")
                articles = researcher_response.content
                # Add the articles to the session state
                self.session_state["articles"] = articles.model_dump()

        # If no articles were found, return
        if articles is None or len(articles.articles) == 0:
            return RunResponse(
                run_id=self.run_id,
                content=f"Sorry could not find any articles on the topic: {topic}",
            )

        # If there are articles, ask the scraper to get the content of each article
        scraped_articles: Dict[str, ScrapedArticle] = {}
        if use_cache and "scraped_articles" in self.session_state:
            for scraped_article in self.session_state["scraped_articles"]:
                try:
                    validated_scraped_article = ScrapedArticle.model_validate(scraped_article)
                    scraped_articles[validated_scraped_article.url] = validated_scraped_article
                except Exception as e:
                    logger.warning(f"Could not read scraped article from session state: {e}")
            logger.info(f"Found {len(scraped_articles)} scraped articles in session state.")

        # Scrape the articles that are not in the session state
        for article in articles.articles:
            if article.url in scraped_articles:
                logger.info(f"Found scraped article in session state: {article.url}")
                continue

            scraper_response: RunResponse = self.scraper.run(article.url)
            if scraper_response and scraper_response.content and isinstance(scraper_response.content, ScrapedArticle):
                scraped_articles[scraper_response.content.url] = scraper_response.content

        # Write a report
        logger.info("Writing final report")
        writer_input = {
            "topic": topic,
            "articles": {article.url: article.model_dump() for article in articles.articles},
        }
        return self.writer.run(json.dumps(writer_input, indent=4))


# Create the workflow
generate_news_report = GenerateNewsReport(
    session_id="generate-report-ibm-hashicorp-acquisition",
    storage=SqlWorkflowStorage(
        table_name="generate_news_report_workflows",
        db_file="tmp/workflows.db",
    ),
)

# Run workflow
report: RunResponse = generate_news_report.run(topic="IBM Hashicorp Acquisition", use_cache=True)

# Print the response
pprint_run_response(report, markdown=True)
