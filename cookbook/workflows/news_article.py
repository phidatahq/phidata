from textwrap import dedent
from typing import Optional

from pydantic import BaseModel, Field

from phi.agent import Agent, AgentResponse
from phi.model.openai import OpenAIChat
from phi.workflow import Workflow
from phi.tools.duckduckgo import DuckDuckGo
from phi.utils.log import logger


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")


class NewsArticles(BaseModel):
    articles: list[NewsArticle]


class WriteNewsReport(Workflow):
    researcher: Agent = Agent(
        name="Researcher",
        model=OpenAIChat(),
        tools=[DuckDuckGo()],
        description="Given a topic, search for 5 articles and return the 3 most relevant articles.",
        response_model=NewsArticles,
    )

    def run(self, topic: str):
        logger.info(f"Researching articles on: {topic}")
        research: AgentResponse = self.researcher.run(topic)
        if research.content and isinstance(research.content, NewsArticles) and research.content.articles:
            logger.info(f"Research identified {len(research.content.articles)} articles.")
        else:
            logger.error("No articles found.")
            return

        logger.info("Reading each article and writing a report.")
        # writer.print_response(research.content.model_dump_json(indent=2), markdown=True, show_message=False)


# Run workflow
WriteNewsReport(debug_mode=True).run(topic="IBM Hashicorp Acquisition")
