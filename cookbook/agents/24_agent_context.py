import json
import httpx
from typing import Optional

from phi.agent import Agent
from phi.utils.log import logger


def get_top_hackernews_stories(agent: Agent, num_stories: Optional[int]) -> str:
    """Use this function to get top stories from Hacker News.

    Args:
        num_stories (int): Number of stories to return. Defaults to 10.

    Returns:
        str: JSON string of top stories.
    """

    logger.info(f"Agent context: {agent.context}")

    # Fetch top story IDs
    response = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    story_ids = response.json()

    # Fetch story details
    stories = []
    for story_id in story_ids[:num_stories]:
        story_response = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        story = story_response.json()
        if "text" in story:
            story.pop("text", None)
        stories.append(story)
    return json.dumps(stories)


agent = Agent(
    tools=[get_top_hackernews_stories],
    show_tool_calls=True,
    markdown=True,
    context={"id": "123"},
)
agent.print_response("Summarize the top story on hackernews?", stream=True)
