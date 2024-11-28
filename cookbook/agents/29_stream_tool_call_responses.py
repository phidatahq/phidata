import json
from typing import Iterator

import httpx
from phi.agent import Agent
from phi.tools import tool, FunctionCall


def pre_hook(function_call: FunctionCall):
    print(f"Pre-hook: {function_call.function.name}")
    print(f"Arguments: {function_call.arguments}")
    print(f"Result: {function_call.result}")


def post_hook(function_call: FunctionCall):
    print(f"Post-hook: {function_call.function.name}")
    print(f"Arguments: {function_call.arguments}")
    print(f"Result: {function_call.result}")


@tool(show_result=True, stop_after_call=True, pre_hook=pre_hook, post_hook=post_hook)
def get_top_hackernews_stories(agent: Agent) -> Iterator[str]:
    num_stories = agent.context.get("num_stories", 5) if agent.context else 5

    # Fetch top story IDs
    response = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    story_ids = response.json()

    # Yield story details
    for story_id in story_ids[:num_stories]:
        story_response = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        story = story_response.json()
        if "text" in story:
            story.pop("text", None)
        yield json.dumps(story)


agent = Agent(
    context={
        "num_stories": 3,
    },
    tools=[get_top_hackernews_stories],
    markdown=True,
    show_tool_calls=True,
)
agent.print_response("What are the top hackernews stories?", stream=True)
