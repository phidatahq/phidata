import json
from typing import Iterator

import httpx
from rich.prompt import Prompt
from rich.pretty import pprint

from phi.agent import Agent, Message
from phi.tools import tool, FunctionCall, StopAgentRun, RetryAgentRun

# This is the console instance used by phi
# We can use this to stop and restart the live display and ask for user confirmation
from phi.cli.console import console


def pre_hook():
    raise RetryAgentRun(
        "Tool call cancelled by user.",
        user_message="You must apologize for this mistake and stop any further execution, no more tool calls.",
    )
    # raise RetryAgentRun(
    #     "Tool call cancelled by user, you must apologize for this mistake and stop any further execution, no more tool calls.",
    # )
    # raise StopAgentRun(
    #     "Tool call cancelled by user, you must apologize for this mistake.",
    #     agent_message="Hi, I'm sorry you don't want to continue. Is there anything else I can help you with?",
    # )
    # raise StopAgentRun(
    #     "Tool call cancelled by user, you must apologize for this mistake.",
    #     messages=[
    #         Message(
    #             role="assistant",
    #             content="Hi, I'm sorry you don't want to continue. Is there anything else I can help you with?",
    #         )
    #     ],
    # )

    # # Get the live display instance from the console
    # live = console._live

    # # Stop the live display temporarily so we can ask for user confirmation
    # live.stop()

    # # Ask for confirmation
    # console.print(f"\nAbout to run [bold blue]{function_call.function.name}[/]")
    # message = Prompt.ask("Do you want to continue?", choices=["y", "n"], default="y").strip().lower()

    # # Clear the console
    # console.clear()

    # # Restart the live display
    # live.start()

    # # If the user does not want to continue, raise a StopExecution exception
    # if message != "y":
    #     raise StopAgentRun(
    #         "Tool call cancelled by user, you must apologize for this mistake.",
    #         messages=[
    #             Message(
    #                 role="assistant",
    #                 content="Hi, I'm sorry you don't want to continue. Is there anything else I can help you with?",
    #             )
    #         ],
    #     )


def post_hook(function_call: FunctionCall):
    print(f"Post-hook: {function_call.function.name}")
    print(f"Arguments: {function_call.arguments}")
    print(f"Result: {function_call.result}")


@tool(pre_hook=pre_hook, post_hook=post_hook)
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


# Initialize the agent
agent = Agent(
    context={
        "num_stories": 2,
    },
    tools=[get_top_hackernews_stories],
    markdown=True,
    show_tool_calls=True,
)

# Run the agent
agent.print_response("What are the top hackernews stories?", stream=True)

# Print the metrics
print("---" * 5, "Aggregated Metrics", "---" * 5)
pprint(agent.run_response.messages)
