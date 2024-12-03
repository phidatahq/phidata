"""
1. Install dependencies using: `pip install openai duckduckgo-search sqlalchemy phidata`
2. Run the script using: `python cookbook/workflows/blog_post_streaming.py`
"""

import json
from typing import Optional, Iterator

from phi.playground.playground import Playground
from phi.storage.workflow.postgres import PgWorkflowStorage
from pydantic import BaseModel, Field

from phi.agent import Agent
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.playground import serve_workflow_playground_app
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

    def get_cached_blog_post(self, topic: str) -> Optional[dict]:
        if "blog_posts" in self.session_state:
            for cached_blog_post in self.session_state["blog_posts"]:
                if cached_blog_post["topic"] == topic:
                    return cached_blog_post
        return None

    def add_cached_blog_post(self, topic: str, blog_post: str):
        if "blog_posts" not in self.session_state:
            self.session_state["blog_posts"] = []
        self.session_state["blog_posts"].append({"topic": topic, "blog_post": blog_post})

    def search_web(self, topic: str) -> Optional[SearchResults]:
        search_results: Optional[SearchResults] = None
        num_tries = 0

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

    def run(self, topic: str, use_cache: bool = True) -> Iterator[RunResponse]:
        logger.info(f"Generating a blog post on: {topic}")

        # Use the cached blog post if use_cache is True
        if use_cache and (cached_blog_post := self.get_cached_blog_post(topic)):
            logger.info("Found cached blog post")
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content=cached_blog_post["blog_post"],
            )
            return

        # Step 1: Search the web for articles on the topic
        search_results = self.search_web(topic)

        # If no search_results are found for the topic, end the workflow
        if search_results is None or len(search_results.articles) == 0:
            yield RunResponse(
                run_id=self.run_id,
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find any articles on the topic: {topic}",
            )
            return

        # Step 2: Write a blog post
        logger.info("Writing blog post")
        # Prepare the input for the writer
        writer_input = {
            "topic": topic,
            "articles": [v.model_dump() for v in search_results.articles],
        }
        # Run the writer and yield the response
        yield from self.writer.run(json.dumps(writer_input, indent=4), stream=True)

        # Save the blog post in the session state for future runs
        content: Optional[str] = self.writer.run_response.content
        if content:
            self.add_cached_blog_post(topic, content)


# Create the workflow
generate_blog_post = BlogPostGenerator(
    storage=PgWorkflowStorage(
        table_name="generate_blog_post_workflows",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)

app = Playground(workflows=[generate_blog_post]).get_app()

if __name__ == "__main__":
    serve_workflow_playground_app("agent_workflow_ui:app", reload=True)
