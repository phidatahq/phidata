import json
from typing import Iterator

import httpx
from rich.console import Console
from rich.prompt import Prompt
from rich.pretty import pprint

from phi.agent import Agent
from phi.tools import tool, FunctionCall, StopAgentRun, RetryAgentRun  # noqa

# This is the console instance used by the print_response method
# We can use this to stop and restart the live display and ask for user confirmation
console = Console()


def pre_hook(fc: FunctionCall):
    # Get the live display instance from the console
    live = console._live

    # Stop the live display temporarily so we can ask for user confirmation
    live.stop()  # type: ignore

    # Ask for confirmation
    console.print(f"\nAbout to run [bold blue]{fc.function.name}[/]")
    message = Prompt.ask("Do you want to continue?", choices=["y", "n"], default="y").strip().lower()

    # Restart the live display
    live.start()  # type: ignore

    # If the user does not want to continue, raise a StopExecution exception
    if message != "y":
        raise StopAgentRun(
            "Tool call cancelled by user",
            agent_message="Stopping execution as permission was not granted.",
        )


@tool(pre_hook=pre_hook)
def get_top_hackernews_stories(num_stories: int) -> Iterator[str]:
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


# Initialize the agent
agent = Agent(tools=[get_top_hackernews_stories], markdown=True, show_tool_calls=True)

# Run the agent
agent.print_response("What are the top 2 hackernews stories?", stream=True, console=console)

# View all messages
pprint(agent.run_response.messages)
