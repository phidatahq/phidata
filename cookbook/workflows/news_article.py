"""Please install dependencies using:
pip install openai duckduckgo-search newspaper4k lxml_html_clean phidata
"""

from textwrap import dedent
from typing import Optional

from pydantic import BaseModel, Field

from phi.agent import Agent, RunResponse
from phi.workflow import Workflow
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


class NewsReporter(Workflow):
    researcher: Agent = Agent(
        tools=[DuckDuckGo()],
        description="Given a topic, search for 5 articles and return the 3 most relevant articles.",
        response_model=NewsArticles,
    )

    writer: Agent = Agent(
        tools=[Newspaper4k()],
        description="You are a Senior NYT Editor and your task is to write a NYT cover story due tomorrow.",
        instructions=[
            "You will be provided with news articles and their links.",
            "Carefully read each article and think about the contents",
            "Then generate a final New York Times worthy article in the <article_format> provided below.",
            "Break the article into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Give the section relevant titles and provide details/facts/processes in each section."
            "Ignore articles that you cannot read or understand.",
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

        ### Takeaways
        {provide key takeaways from the article}

        ### References
        - [Title](url)
        - [Title](url)
        - [Title](url)
        </article_format>
        """),
    )

    def run(self, topic: str) -> RunResponse:
        logger.info(f"Researching articles on: {topic}")
        research: RunResponse = self.researcher.run(topic)
        if research and research.content and isinstance(research.content, NewsArticles) and research.content.articles:
            logger.info(f"Researcher identified {len(research.content.articles)} articles.")
        else:
            return RunResponse(
                run_id=self.run_id,
                content=f"Sorry could not find any articles on the topic: {topic}",
            )

        logger.info("Reading each article and writing a report.")
        return self.writer.run(research.content.model_dump_json(indent=2))


# Run workflow
report: RunResponse = NewsReporter(debug_mode=False).run(topic="IBM Hashicorp Acquisition")
# Print the response
pprint_run_response(report, markdown=True)
