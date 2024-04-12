import json
import httpx

from phi.assistant.team import Assistant
from phi.utils.log import logger


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
        user = httpx.get(f"https://hacker-news.firebaseio.com/v0/user/{username}.json").json()
        user_details = {
            "id": user.get("user_id"),
            "karma": user.get("karma"),
            "about": user.get("about"),
            "total_items_submitted": len(user.get("submitted", [])),
        }
        if user.get("submitted"):
            top_submitted = [i for i in user.get("submitted")[:200]]
            submitted_stories = []
            for story_id in top_submitted:
                story_response = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                story = story_response.json()
                story["username"] = story.get("by")
                submitted_stories.append(story)
            # Get top 10 stories by score
            top_stories = sorted(
                submitted_stories, key=lambda x: (x.get("score") if "score" in x else 0), reverse=True
            )[:10]
            top_story_details = []
            for story in top_stories:
                if "title" not in story:
                    continue
                story_details = {
                    "id": story.get("id"),
                    "title": story.get("title"),
                    "url": story.get("url"),
                    "author": story.get("by"),
                    "type": story.get("type"),
                    "score": story.get("score"),
                    "total_comments": story.get("descendants"),
                }
                if "text" in story:
                    story_details["text"] = story.get("text")
                top_story_details.append(story_details)
            user_details["top_stories"] = top_story_details
        return json.dumps(user_details)
    except Exception as e:
        logger.exception(e)
        return f"Error getting user details: {e}"


hn_top_stories = Assistant(
    name="HackerNews Top Stories",
    role="Research top hackernews stories",
    tools=[get_top_hackernews_stories],
    show_tool_calls=True,
)
hn_user_researcher = Assistant(
    name="HackerNews User Researcher",
    role="Get information about hackernews users",
    tools=[get_user_details],
    show_tool_calls=True,
)

hn_assistant = Assistant(name="HackerNews Assistant", team=[hn_top_stories, hn_user_researcher], debug_mode=True)
hn_assistant.print_response("Tell me about the users with the top 2 stores on hackernews?", markdown=True)
