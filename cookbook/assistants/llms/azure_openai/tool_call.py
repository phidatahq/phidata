import json
import httpx

from phi.assistant import Assistant
from phi.llm.azure import AzureOpenAIChat


def get_top_hackernews_stories(num_stories: int = 10) -> str:
    """Use this function to get top stories from Hacker News.

    Args:
        num_stories (int): Number of stories to return. Defaults to 10.

    Returns:
        str: JSON string of top stories.
    """

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


assistant = Assistant(
    llm=AzureOpenAIChat(model="gpt-35-turbo"),  # model="deployment_name"
    tools=[get_top_hackernews_stories],
    show_tool_calls=True,
)
assistant.print_response("Summarize the top stories on hackernews?")
