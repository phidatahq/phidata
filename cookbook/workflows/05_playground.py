"""
1. Install dependencies using: `pip install openai duckduckgo-search sqlalchemy 'fastapi[standard]' phidata`
2. Run the script using: `python cookbook/workflows/05_playground.py`
"""

import json
from textwrap import dedent
from typing import Dict, Optional, Iterator

from phi.tools.newspaper4k import Newspaper4k
from phi.tools.yfinance import YFinanceTools
from pydantic import BaseModel, Field

from phi.agent import Agent
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.playground import Playground, serve_playground_app
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.utils.log import logger


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")


class SearchResults(BaseModel):
    articles: list[NewsArticle]


class BlogPostGenerator(Workflow):
    description: str = "Generate a blog post on a given topic."

    searcher: Agent = Agent(
        tools=[DuckDuckGo()],
        instructions=["Given a topic, search for 20 articles and return the 5 most relevant articles."],
        response_model=SearchResults,
    )

    writer: Agent = Agent(
        instructions=[
            "You will be provided with a topic and a list of top articles on that topic.",
            "Carefully read each article and generate a New York Times worthy blog post on that topic.",
            "Break the blog post into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Always provide sources, do not make up information or sources.",
        ],
    )

    def get_cached_blog_post(self, topic: str) -> Optional[str]:
        logger.info("Checking if cached blog post exists")
        if "blog_posts" in self.session_state and topic in self.session_state["blog_posts"]:
            logger.info("Found cached blog post")
            return self.session_state["blog_posts"][topic]
        return None

    def get_search_results(self, topic: str) -> Optional[SearchResults]:
        num_tries = 0
        search_results: Optional[SearchResults] = None
        # Run until we get a valid search results
        while search_results is None and num_tries < 3:
            try:
                num_tries += 1
                searcher_response: RunResponse = self.searcher.run(topic)
                if (
                    searcher_response
                    and searcher_response.content
                    and isinstance(searcher_response.content, SearchResults)
                ):
                    logger.info(f"Searcher found {len(searcher_response.content.articles)} articles.")
                    search_results = searcher_response.content
                else:
                    logger.warning("Searcher response invalid, trying again...")
            except Exception as e:
                logger.warning(f"Error running searcher: {e}")
        return search_results

    def write_blog_post(self, topic: str, search_results: SearchResults) -> Iterator[RunResponse]:
        logger.info("Writing blog post")
        # Prepare the input for the writer
        writer_input = {"topic": topic, "articles": [v.model_dump() for v in search_results.articles]}
        # Run the writer and yield the response
        yield from self.writer.run(json.dumps(writer_input, indent=4), stream=True)
        # Save the blog post in the session state for future runs
        if "blog_posts" not in self.session_state:
            self.session_state["blog_posts"] = {}
        logger.info(f"Saving blog post for topic: {topic}")
        self.session_state["blog_posts"][topic] = self.writer.run_response.content

    def run(self, topic: str, use_cache: bool = True) -> Iterator[RunResponse]:
        logger.info(f"Generating a blog post on: {topic}")

        # Use the cached blog post if use_cache is True
        if use_cache:
            cached_blog_post = self.get_cached_blog_post(topic)
            if cached_blog_post:
                yield RunResponse(content=cached_blog_post, event=RunEvent.workflow_completed)
                return

        # Search the web for articles on the topic
        search_results: Optional[SearchResults] = self.get_search_results(topic)
        # If no search_results are found for the topic, end the workflow
        if search_results is None or len(search_results.articles) == 0:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find any articles on the topic: {topic}",
            )
            return

        # Write a blog post
        yield from self.write_blog_post(topic, search_results)


# Instantiate the workflow
generate_blog_post = BlogPostGenerator(
    storage=SqlWorkflowStorage(
        table_name="generate_blog_post_workflows",
        db_file="tmp/workflows.db",
    ),
)


class ScrapedArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")
    content: Optional[str] = Field(
        ...,
        description="Content of the in markdown format if available. Return None if the content is not available or does not make sense.",
    )


class GenerateNewsReport(Workflow):
    description: str = "Generate a comprehensive news report on a given topic."

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

    def get_report_from_cache(self, use_cached_report: bool, topic: str) -> Iterator[RunResponse]:
        if use_cached_report and "reports" in self.session_state:
            logger.info("Checking if cached report exists")
            for cached_report in self.session_state["reports"]:
                if cached_report["topic"] == topic:
                    yield RunResponse(
                        run_id=self.run_id,
                        event=RunEvent.workflow_completed,
                        content=cached_report["report"],
                    )
                    return

    def search_web(self, use_search_cache: bool, topic: str) -> Optional[SearchResults]:
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

        return search_results

    def scrape_articles(self, use_scrape_cache: bool, search_results: SearchResults) -> Dict[str, ScrapedArticle]:
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

        return scraped_articles

    def run(
        self, topic: str, use_search_cache: bool = True, use_scrape_cache: bool = True, use_cached_report: bool = False
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
        yield from self.get_report_from_cache(use_cached_report, topic)

        ####################################################
        # Step 1: Search the web for articles on the topic
        ####################################################

        search_results: Optional[SearchResults] = self.search_web(use_search_cache, topic)
        if search_results is None:
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find any articles on the topic: {topic}",
            )
            return

        ####################################################
        # Step 2: Scrape each article
        ####################################################

        scraped_articles: Dict[str, ScrapedArticle] = self.scrape_articles(use_scrape_cache, search_results)

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
        yield from self.writer.run(json.dumps(writer_input, indent=4), stream=True)

        # 3.2: Save the writer_response in the session state
        if "reports" not in self.session_state:
            self.session_state["reports"] = []
        self.session_state["reports"].append({"topic": topic, "report": self.writer.run_response.content})


# Instantiate the workflow
generate_news_report = GenerateNewsReport(
    storage=SqlWorkflowStorage(
        table_name="generate_news_report_workflows",
        db_file="tmp/workflows.db",
    ),
)


class InvestmentAnalyst(Workflow):
    description: str = (
        "Produce a research report on a list of companies and then rank them based on investment potential."
    )

    stock_analyst: Agent = Agent(
        tools=[YFinanceTools(company_info=True, analyst_recommendations=True, company_news=True)],
        description="You are a Senior Investment Analyst for Goldman Sachs tasked with producing a research report for a very important client.",
        instructions=[
            "You will be provided with a list of companies to write a report on.",
            "Get the company information, analyst recommendations and news for each company",
            "Generate an in-depth report for each company in markdown format with all the facts and details."
            "Note: This is only for educational purposes.",
        ],
        expected_output="Report in markdown format",
    )

    research_analyst: Agent = Agent(
        name="Research Analyst",
        description="You are a Senior Investment Analyst for Goldman Sachs tasked with producing a ranked list of companies based on their investment potential.",
        instructions=[
            "You will write a research report based on the information provided by the Stock Analyst.",
            "Think deeply about the value of each stock.",
            "Be discerning, you are a skeptical investor focused on maximising growth.",
            "Then rank the companies in order of investment potential, with as much detail about your decision as possible.",
            "Prepare a markdown report with your findings with as much detail as possible.",
        ],
        expected_output="Report in markdown format",
    )

    investment_lead: Agent = Agent(
        name="Investment Lead",
        description="You are a Senior Investment Lead for Goldman Sachs tasked with investing $100,000 for a very important client.",
        instructions=[
            "You have a stock analyst and a research analyst on your team.",
            "The stock analyst has produced a preliminary report on a list of companies, and then the research analyst has ranked the companies based on their investment potential.",
            "Review the report provided by the research analyst and produce a investment proposal for the client.",
            "Provide the amount you'll exist in each company and a report on why.",
        ],
    )

    def run(self, companies: str) -> Iterator[RunResponse]:
        logger.info(f"Getting investment reports for companies: {companies}")
        initial_report: RunResponse = self.stock_analyst.run(companies)
        if initial_report is None or not initial_report.content:
            yield RunResponse(run_id=self.run_id, content="Sorry, could not get the stock analyst report.")
            return

        logger.info("Ranking companies based on investment potential.")
        ranked_companies: RunResponse = self.research_analyst.run(initial_report.content)
        if ranked_companies is None or not ranked_companies.content:
            yield RunResponse(run_id=self.run_id, content="Sorry, could not get the ranked companies.")
            return

        logger.info("Reviewing the research report and producing an investment proposal.")
        yield from self.investment_lead.run(ranked_companies.content, stream=True)


investment_analyst = InvestmentAnalyst(
    storage=SqlWorkflowStorage(
        table_name="investment_analyst_workflows",
        db_file="tmp/workflows.db",
    ),
)

app = Playground(workflows=[generate_blog_post, generate_news_report, investment_analyst]).get_app()

if __name__ == "__main__":
    serve_playground_app("05_playground:app", reload=True)
