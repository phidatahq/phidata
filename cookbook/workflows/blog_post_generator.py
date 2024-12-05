"""
1. Install dependencies using: `pip install openai exa_py sqlalchemy phidata`
2. Run the script using: `python cookbook/workflows/blog_post_generator.py`
"""

import json
from typing import Optional, Iterator

from pydantic import BaseModel, Field

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.workflow import Workflow, RunResponse, RunEvent
from phi.storage.workflow.sqlite import SqlWorkflowStorage
from phi.tools.exa import ExaTools
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger


class NewsArticle(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article if available.")


class SearchResults(BaseModel):
    articles: list[NewsArticle]


class BlogPostGenerator(Workflow):
    # This description is only used in the workflow UI
    description: str = "Generate a blog post on a given topic."

    searcher: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[ExaTools(type="keyword")],
        instructions=["Given a topic, search for the top 5 articles."],
        response_model=SearchResults,
        structured_outputs=True,
    )

    writer: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions=[
            "You will be provided with a topic and a list of top articles on that topic.",
            "Carefully read each article and generate a New York Times worthy blog post on that topic.",
            "Break the blog post into sections and provide key takeaways at the end.",
            "Make sure the title is catchy and engaging.",
            "Always provide sources, do not make up information or sources.",
        ],
        markdown=True,
    )

    def get_cached_blog_post(self, topic: str) -> Optional[str]:
        logger.info("Checking if cached blog post exists")
        return self.session_state.get("blog_posts", {}).get(topic)

    def add_blog_post_to_cache(self, topic: str, blog_post: Optional[str]):
        logger.info(f"Saving blog post for topic: {topic}")
        self.session_state.setdefault("blog_posts", {})
        self.session_state["blog_posts"][topic] = blog_post

    def get_search_results(self, topic: str) -> Optional[SearchResults]:
        MAX_ATTEMPTS = 3

        for attempt in range(MAX_ATTEMPTS):
            try:
                searcher_response: RunResponse = self.searcher.run(topic)

                # Check if we got a valid response
                if not searcher_response or not searcher_response.content:
                    logger.warning(f"Attempt {attempt + 1}/{MAX_ATTEMPTS}: Empty searcher response")
                    continue
                # Check if the response is of the expected SearchResults type
                if not isinstance(searcher_response.content, SearchResults):
                    logger.warning(f"Attempt {attempt + 1}/{MAX_ATTEMPTS}: Invalid response type")
                    continue

                article_count = len(searcher_response.content.articles)
                logger.info(f"Found {article_count} articles on attempt {attempt + 1}")
                return searcher_response.content

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{MAX_ATTEMPTS} failed: {str(e)}")

        logger.error(f"Failed to get search results after {MAX_ATTEMPTS} attempts")
        return None

    def write_blog_post(self, topic: str, search_results: SearchResults) -> Iterator[RunResponse]:
        logger.info("Writing blog post")
        # Prepare the input for the writer
        writer_input = {"topic": topic, "articles": [v.model_dump() for v in search_results.articles]}
        # Run the writer and yield the response
        yield from self.writer.run(json.dumps(writer_input, indent=4), stream=True)
        # Save the blog post in the cache
        self.add_blog_post_to_cache(topic, self.writer.run_response.content)

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


# Run the workflow if the script is executed directly
if __name__ == "__main__":
    from rich.prompt import Prompt

    # Get topic from user
    topic = Prompt.ask(
        "[bold]Enter a blog post topic[/bold]\n✨",
        default="Why Cats Secretly Run the Internet",
    )

    # Convert the topic to a URL-safe string for use in session_id
    url_safe_topic = topic.lower().replace(" ", "-")

    # Initialize the blog post generator workflow
    # - Creates a unique session ID based on the topic
    # - Sets up SQLite storage for caching results
    generate_blog_post = BlogPostGenerator(
        session_id=f"generate-blog-post-on-{url_safe_topic}",
        storage=SqlWorkflowStorage(
            table_name="generate_blog_post_workflows",
            db_file="tmp/workflows.db",
        ),
    )

    # Execute the workflow with caching enabled
    # Returns an iterator of RunResponse objects containing the generated content
    blog_post: Iterator[RunResponse] = generate_blog_post.run(topic=topic, use_cache=True)

    # Print the response
    pprint_run_response(blog_post, markdown=True)
