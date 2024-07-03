import json
import httpx

from phi.assistant import Assistant
from phi.utils.log import logger


def get_top_hackernews_stories(num_stories: int = 10) -> str:
    """Use this function to get top stories from Hacker News.

    Args:
        num_stories (int): Number of stories to return. Defaults to 10.

    Returns:
        str: JSON string of top stories.
    """

    # Fetch top story IDs
    logger.info(f"Getting top {num_stories} stories from Hacker News")
    response = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    story_ids = response.json()

    # Fetch story details
    stories = []
    for story_id in story_ids[:num_stories]:
        story_response = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        story = story_response.json()
        story["username"] = story["by"]
        stories.append(story)
    return json.dumps(stories)


def get_user_details(username: str) -> str:
    """Use this function to get the details of a Hacker News user using their username.

    Args:
        username (str): Username of the user to get details for.

    Returns:
        str: JSON string of the user details.
    """

    try:
        logger.info(f"Getting details for user: {username}")
        user = httpx.get(f"https://hacker-news.firebaseio.com/v0/user/{username}.json").json()
        user_details = {
            "id": user.get("user_id"),
            "karma": user.get("karma"),
            "about": user.get("about"),
            "total_items_submitted": len(user.get("submitted", [])),
        }
        return json.dumps(user_details)
    except Exception as e:
        logger.exception(e)
        return f"Error getting user details: {e}"


hn_top_stories = Assistant(
    name="HackerNews Top Stories",
    tools=[get_top_hackernews_stories],
    role="Get the top stories on Hacker News.",
    show_tool_calls=True,
)
hn_user_researcher = Assistant(
    name="HackerNews User Researcher",
    tools=[get_user_details],
    role="Get information about Hacker News users.",
    show_tool_calls=True,
)

hn_assistant = Assistant(
    name="HackerNews Assistant",
    team=[hn_top_stories, hn_user_researcher],
    show_tool_calls=True,
    save_output_to_file="wip/top_hackernews_users.md",
)
hn_assistant.print_response(
    "Write an engaging article about the users with the top 2 stories on hackernews", markdown=True
)
