from typing import Optional, Iterator

from pydantic import BaseModel, Field

from phi.agent import Agent, AgentResponse
from phi.workflow import Workflow
from phi.tools.duckduckgo import DuckDuckGo
from phi.utils.pprint import pprint_agent_response_stream
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
        tools=[DuckDuckGo()],
        description="Given a topic, search for 5 articles and return the 3 most relevant articles.",
        response_model=NewsArticles,
    )

    writer: Agent = Agent()

    def run(self, topic: str) -> Iterator[AgentResponse]:
        logger.info(f"Researching articles on: {topic}")
        # research: AgentResponse = self.researcher.run(topic)
        # if research.content and isinstance(research.content, NewsArticles) and research.content.articles:
        #     logger.info(f"Research identified {len(research.content.articles)} articles.")
        # else:
        #     logger.error("No articles found.")
        #     return

        logger.info("Reading each article and writing a report.")
        # writer.print_response(research.content.model_dump_json(indent=2), markdown=True, show_message=False)
        yield from self.writer.run(f"write 1 sentence on {topic}", stream=True)


# Run workflow
story = WriteNewsReport(debug_mode=False).run(topic="avocado toast")
pprint_agent_response_stream(story, markdown=True, show_time=True)
