"""
1. Install dependencies using: `pip install openai duckduckgo-search sqlalchemy phidata`
2. Run the script using: `python cookbook/workflows/blog_post_generator.py`
"""

import json
from typing import Optional, Iterator, List

from pydantic import BaseModel, Field

from phi.agent import Agent
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.tools.duckduckgo import DuckDuckGo
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")


class SearchResults(BaseModel):
    articles: List[NewsArticle]


class BlogPostGenerator(Workflow):
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


# The topic to generate a blog post on
topic = "US Elections 2024"

# Instantiate the workflow
generate_blog_post = BlogPostGenerator(
    session_id=f"generate-blog-post-on-{topic}",
    storage=SqlWorkflowStorage(
        table_name="generate_blog_post_workflows",
        db_file="tmp/workflows.db",
    ),
)

# Run workflow
blog_post: Iterator[RunResponse] = generate_blog_post.run(topic=topic, use_cache=True)

# Print the response
pprint_run_response(blog_post, markdown=True)
