import json
import httpx

from phi.agent import Agent


def get_top_hackernews_stories(num_stories: int = 5) -> str:
    # Get top stories
    stories = [
        {
            k: v
            for k, v in httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{id}.json").json().items()
            if k != "text"
        }
        for id in httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:num_stories]
    ]
    return json.dumps(stories)


Agent(
    add_context=True,
    context={"top_hackernews_stories": get_top_hackernews_stories},
).print_response("Summarize the top stories on hackernews?", stream=True, markdown=True)
